import os
import time
import json
import random
import logging
import pandas as pd
from typing import TypedDict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from langgraph.graph import StateGraph, END
from tavily import TavilyClient
from langchain_ollama import ChatOllama
import instructor 
from pydantic import BaseModel

# ────────────────────────────── CONFIG ──────────────────────────────
INPUT_XLSX = "/shared_data/linkedininput/profili_google_Linkedin_40_ciclo_rev.xlsx"
SHEET_NAME = "40th cycle + cotutelle 39th"
COLUMNS = ["Cognome", "Nome", "LINKEDIN"]
OUTPUT_JSON = "/shared_data/linkedinoutput/linkedin_profiles.json"
OUTPUT_CSV = "/shared_data/linkedinoutput/linkedin_profiles.csv"
LOG_DIR = "/shared_data/logs"
LOG_FILE = os.path.join(LOG_DIR, "linkedin_crawler.log")

# Ensure output and log directories exist
os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ────────────────────────────── CLIENTS ──────────────────────────────
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

llm = ChatOllama(
    model="llama3.2:3b",
    temperature=0,
    base_url=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/")
)

# Wrap LLM with Instructor for structured JSON output
llm_json = Instructor()
profile: Profile = llm_json(prompt, llm=llm, response_model=Profile)

# ────────────────────────────── SCHEMA ──────────────────────────────
class Experience(BaseModel):
    company: str
    title: str
    years: str

class Profile(BaseModel):
    name: str
    title: str
    current_company: str
    location: str
    experience: List[Experience]

# ────────────────────────────── GRAPH ──────────────────────────────
class GraphState(TypedDict, total=False):
    url: str
    raw_profile: str
    profile_json: dict

# ---- Tavily Extraction Node ----
def extract_profile(state: GraphState) -> GraphState:
    url = state["url"]
    try:
        res = tavily.extract(urls=[url])
        if not res.get("results"):
            raise ValueError("Empty Tavily result")
        text = res["results"][0].get("raw_content") or res["results"][0].get("content", "")
        return {"raw_profile": text}
    except Exception as e:
        logging.error(f"Tavily extraction failed for {url}: {e}")
        return {"raw_profile": ""}

# ---- LLM Formatting Node using Instructor ----
def format_profile(state: GraphState) -> GraphState:
    raw = state.get("raw_profile", "").strip()
    if not raw:
        return {"profile_json": {}}

    prompt = f"""
Extract the following fields from this LinkedIn profile text and return as JSON:

- name
- title
- current_company
- location
- experience (only most recent job: company, title, years)

Text:
\"\"\"{raw}\"\"\"
"""
    try:
        profile: Profile = llm_json(prompt, response_model=Profile)
        return {"profile_json": profile.dict()}
    except Exception as e:
        logging.error(f"LLM formatting failed for {state.get('url')}: {e}")
        return {"profile_json": {}}

# Build Graph
builder = StateGraph(GraphState)
builder.add_node("extract", extract_profile)
builder.add_node("format", format_profile)
builder.set_entry_point("extract")
builder.add_edge("extract", "format")
builder.add_edge("format", END)
graph = builder.compile()

# ────────────────────────────── CORE PROCESS ──────────────────────────────
def process_profile(row) -> dict:
    url = row["LINKEDIN"]
    if not isinstance(url, str) or not url.startswith("http"):
        logging.warning(f"Skipping invalid URL: {url}")
        return None

    time.sleep(random.uniform(5, 15))  # polite delay
    try:
        out = graph.invoke({"url": url})
        logging.info(f"Processed {url}")
        profile_json = out.get("profile_json", {})
        return {
            "Cognome": row["Cognome"],
            "Nome": row["Nome"],
            "LINKEDIN": url,
            **profile_json
        }
    except Exception as e:
        logging.error(f"Graph invoke failed for {url}: {e}")
        return None

# ────────────────────────────── MAIN ──────────────────────────────
def main():
    df = pd.read_excel(INPUT_XLSX, sheet_name=SHEET_NAME, usecols=COLUMNS)
    results = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_profile, row) for _, row in df.iterrows()]

        for i, f in enumerate(as_completed(futures), start=1):
            res = f.result()
            if res:
                results.append(res)

                # Incremental save every 5 profiles
                if i % 5 == 0:
                    pd.DataFrame(results).to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
                    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
                        json.dump(results, f, ensure_ascii=False, indent=2)
                    logging.info(f"Checkpoint: saved {i} profiles")

    # Final save
    pd.DataFrame(results).to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logging.info(f"✅ Done! Written {len(results)} profiles.")

if __name__ == "__main__":
    main()
