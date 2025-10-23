import json
import csv
import os
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from typing import TypedDict

# === LLM Initialization ===
llm = ChatOllama(
    model="llama3.2:3b",
    temperature=0,
    base_url="http://ollama:11434/"
)
print("✅ Ollama initialized.")

# === Graph State Definition ===
class GraphState(TypedDict, total=False):
    raw_profile: str
    employment_summary: str

# === Node Function for LangGraph ===
def summarize_employment(state: GraphState) -> GraphState:
    raw_text = state.get("raw_profile", "").strip()
    if not raw_text:
        return {"employment_summary": ""}

    prompt = f"""
You are an expert summarizer. Given the following profile attributes, 
write a concise summary of the person's current employment status in less than 100 words. In case of 
unknown or missing information, state "Information not available or accessible".
Focus only on the most recent job/position. Return plain text only.

Profile text:
\"\"\"{raw_text}\"\"\"
"""
    try:
        rsp = llm.invoke([HumanMessage(content=prompt)])
        return {"employment_summary": rsp.content.strip()}
    except Exception as e:
        print(f"[ERROR] LLM processing failed: {e}")
        return {"employment_summary": ""}

# === Main Agent Class ===
class EmploymentSummaryAgent:
    def __init__(self,
                 input_path="/shared_data/linkedinoutput/silver/processed_linkedin_employment_copy.json",
                 output_path="/shared_data/linkedinoutput/gold/processed_linkedin_summary.csv"):
        self.input_path = input_path
        self.output_path = output_path

    def process_records(self):
        if not os.path.exists(self.input_path):
            raise FileNotFoundError(f"Input file not found: {self.input_path}")

        with open(self.input_path, "r", encoding="utf-8") as infile, \
            open(self.output_path, "w", newline="", encoding="utf-8") as csvfile:

            records = json.load(infile)
            fieldnames = ["Nome", "Cognome", "Title", "EmploymentSummary", "LinkedInURL"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for line_number, record in enumerate(records, start=1):
                try:
                    current_company = record.get("Azienda attuale", "")
                    current_position = record.get("Occupazione attuale", "")
                    employment_data = record.get("employment_data", {})

                    raw_records = (
                        f"Current Company: {current_company}\n"
                        f"Current Position: {current_position}\n"
                        f"Company Name: {employment_data.get('Company Name', '')}\n"
                        f"Job Position: {employment_data.get('Job Position', '')}\n"
                        f"Company Location: {employment_data.get('Company Location', '')}\n"
                        f"Company Linkedin URL: {employment_data.get('Company Linkedin URL', '')}\n"
                        f"Start Year: {employment_data.get('Start Year', '')}\n"
                        f"Finish Year: {employment_data.get('Finish Year', '')}\n"
                        f"Job Description: {employment_data.get('Job Description', '')}"
                    )

                    # Skip empty profiles
                    if not any([current_company, current_position] + list(employment_data.values())):
                        print(f"[WARN] No profile text found in line {line_number}")
                        continue

                    # Call LLM to summarize
                    state = {"raw_profile": raw_records}
                    out = summarize_employment(state)
                    summary = out.get("employment_summary", "")

                    processed_row = {
                        "Nome": record.get("Nome") or record.get("name", ""),
                        "Cognome": record.get("Cognome") or record.get("surname", ""),
                        "Title": record.get("Titolo") or record.get("Title", ""),
                        "EmploymentSummary": summary,
                        "LinkedInURL": record.get("LinkedIn") or record.get("linkedin", "")
                    }

                    writer.writerow(processed_row)
                    print(f"✅ Processed line {line_number}", flush=True)

                except Exception as e:
                    print(f"[ERROR] Failed at line {line_number}: {e}", flush=True)

        print(f"\n✅ Processing complete! Output saved to: {self.output_path}", flush=True)
# === Run as script ===
if __name__ == "__main__":
    agent = EmploymentSummaryAgent()
    agent.process_records()
