import json
import re
import os
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from typing import TypedDict
from langgraph.graph import StateGraph, END


# === LangGraph State Definition ===
class GraphState(TypedDict, total=False):
    raw_profile: str
    profile_json: str


# === LLM Initialization ===
llm = ChatOllama(
    model="llama3.2:3b",
    temperature=0,
    base_url="http://ollama:11434/"
)
print("✅ Ollama initialized.")


# === Helper Function: Extract Experience Section ===
def extract_experience_snippet(raw_text: str) -> str:
    """Extract the '## Experience' section or first 2500 chars as fallback."""
    if not raw_text:
        return ""

    match = re.search(r"##\s*Experience", raw_text, re.IGNORECASE)
    education = re.search(r"##\sEducation", raw_text, re.IGNORECASE)

    if not match:
        print("[INFO] No '## Experience' section found.")
        return raw_text[:2500]

    start_idx = match.start()
    end_idx = education.start() if education else len(raw_text)
    return raw_text[start_idx:end_idx]


# === Node Function for LangGraph ===
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
  "Start Year": "string",
  "Finish Year": "string",
  "Job Description": "string"
}}

Include ONLY the single most recent employment (if available).

Text to extract from:
\"\"\"{snippet}\"\"\"

Return ONLY a JSON object.
"""

    try:
        rsp = llm.invoke([HumanMessage(content=prompt)])
        return {"profile_json": rsp.content}
    except Exception as e:
        print(f"[ERROR] LLM processing failed: {e}")
        return {"profile_json": "{}"}


# === Main Agent Class ===
class LinkedInEmploymentAgent:
    def __init__(self,
                 input_path="/shared_data/linkedinoutput/bronze/raw_linkedin_total_copy.jsonl",
                 output_path="/shared_data/linkedinoutput/silver/processed_linkedin_employment.json"):
        self.input_path = input_path
        self.output_path = output_path

        # Build the state graph
        builder = StateGraph(GraphState)
        builder.add_node("format", format_profile)
        builder.set_entry_point("format")
        self.graph = builder.compile()

    def process_records(self):
        if not os.path.exists(self.input_path):
            raise FileNotFoundError(f"Input file not found: {self.input_path}")

        processed_rows = []
        with open(self.input_path, "r", encoding="utf-8") as infile:
            for line_number, line in enumerate(infile, start=1):
                try:
                    record = json.loads(line)
                    raw_text = record.pop("raw_linkedin_total", "")
                    if not raw_text:
                        print(f"[WARN] Missing 'raw_linkedin_total' in line {line_number}")
                        continue

                    state = {"raw_profile": raw_text}
                    out = self.graph.invoke(state)
                    profile_json = out.get("profile_json", "{}")

                    record["employment_data"] = json.loads(profile_json)
                    processed_rows.append(record)

                    print(f"✅ Processed line {line_number}")
                except Exception as e:
                    print(f"[ERROR] Failed at line {line_number}: {e}")

            with open(self.output_path, "w", encoding="utf-8") as outfile:
                json.dump(record, outfile, indent=2, ensure_ascii=False)
                outfile.write(",\n")

        print(f"\n✅ Processing complete! Output saved to: {self.output_path}")


# === Run as Script ===
if __name__ == "__main__":
    agent = LinkedInEmploymentAgent()
    agent.process_records()
