from langchain_ollama import ChatOllama
from tavily import TavilyClient
import re
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain.schema import HumanMessage
import os

# === Initialization ===
tavily = TavilyClient(api_key=os.environ['TAVILY_API_KEY'])
print("Tavily client initiated")


url = "https://www.linkedin.com/in/gianvito-urgese-5bb2668a/"

llm = ChatOllama(
    model="llama3.2:3b",
    temperature=0,
    base_url="http://ollama:11434/"
)
print("Ollama initiated, now we will try to crawl the web!")

# === State Definition ===
class GraphState(TypedDict, total=False):
    url: str
    raw_profile: str
    profile_json: str


# === Step 1: Extract Raw Profile ===
def extract_profile(state: GraphState) -> GraphState:
    try:
        res = tavily.extract(urls=[state["url"]])
        text = res["results"][0].get("raw_content", "") if res.get("results") else ""
    except Exception as e:
        print(f"[ERROR] extract failed for {state['url']}: {e}")
        text = ""
    return {"raw_profile": text}


# === Step 2: Trim to '## Experience' Section (300 chars) ===
def extract_experience_snippet(raw_text: str) -> str:
    """Find '## Experience' section and extract 500 chars after it."""
    if not raw_text:
        return ""

    # Find the '## Experience' section, case-insensitive
    match = re.search(r"##\s*Experience", raw_text, re.IGNORECASE)
    education = re.search(r"##\sEducation", raw_text, re.IGNORECASE)
    if not match:
        print("[INFO] No '## Experience' section found.")
        # fallback: just take the first 300 chars of text
        return raw_text[:2500]

    start_idx = match.start()
    end_idx = education.end()
    snippet = raw_text[start_idx:end_idx]
    print(f"[DEBUG] Extracted snippet around '## Experience': {snippet}...")
    return snippet


# === Step 3: Format with LLM ===
def format_profile(state: GraphState) -> GraphState:
    raw = state.get("raw_profile", "").strip()
    snippet = extract_experience_snippet(raw)

    if not snippet:
        print("[INFO] No valid experience text found.")
        return {"profile_json": "{}"}

    prompt = f"""
You are a strict JSON formatter.
Extract the following fields from the given text and return a valid JSON object with no extra word or explanation.

Schema (return keys exactly as shown):
{{
  "Company Name": "string",
  "Job Position": "string",
  "Company Location": "string",
  "Company Linkedin URL": "string",
  "Start Year":"string",
  "Finish Year": "string",
  "Job Description": "string" 
}}

Include ONLY the single most recent employment (if available).

Text to extract from (triple-quoted block):
\"\"\"{snippet}\"\"\"

Return ONLY a JSON object. Do NOT include any explanation or extra text.
"""

    try:
        rsp = llm.invoke([HumanMessage(content=prompt)])
        return {"profile_json": rsp.content}
    except Exception as e:
        print(f"[ERROR] LLM format failed: {e}")
        return {"profile_json": "{}"}


# === Build Graph ===
print("StateGraph is being initiated")
builder = StateGraph(GraphState)
builder.add_node("extract", extract_profile)
builder.add_node("format", format_profile)
builder.set_entry_point("extract")
builder.add_edge("extract", "format")
builder.add_edge("format", END)

graph = builder.compile()

# === Run ===
linkedin_url = url
state = {"url": linkedin_url}

try:
    out = graph.invoke(state)
    print(f"[DEBUG] Output: {out.get('profile_json')}")
except Exception as e:
    print(f"[ERROR] graph.invoke failed: {e}")
