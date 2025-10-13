import pandas as pd
from tavily import TavilyClient
import os
import json
import time
import random

# tavily = TavilyClient(api_key=os.environ['TAVILY_API_KEY'])
print("Tavily client initiated")

input_path = "app/linkedininput/students_linkedin_20230504.xlsx"
output_path = "app/linkedinoutput/bronze/raw_linkedin_total.jsonl"


def rand_gen():
    r1 = random.uniform(0, 30)
    r2 = random.uniform(10, 50)
    if r1 < r2:
        r3 = random.uniform(r1, r2)
    elif r2 < r1:
        r3 = random.uniform(r2, r1)
    else:
        r3 = r1
    return r3


# === Initialization ===
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

input_path = "/linkedininput/students_linkedin_20230504.xlsx"
output_path = "/linkedinoutput/raw_linkedin_total.jsonl"

# === Load Excel file ===
df = pd.read_excel(input_path, sheet_name="students_linkedin_20230504")
df = df.dropna(subset=["Linkedin"])  # drop rows with no URL
print(f"Loaded {len(df)} rows to process.")


# === Helper: safe append to JSONL ===
def append_jsonl(record, filepath):
    """Append one record as JSON to a JSONL file."""
    with open(filepath, "a", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False)
        f.write("\n")


# === Process each row ===
for idx, row in df.iterrows():
    url = str(row["Linkedin"]).strip()
    if not url or not url.startswith("http"):
        print(f"[{idx}] Invalid or missing URL: {url}")
        continue

    row_data = row.to_dict()
    print(f"[{idx}] Extracting {url} ...")

    raw_text = ""
    success = False

    # Try three times
    for attempt in range(3):
        try:
            res = tavily.extract(urls=[url])
            if res.get("results"):
                raw_text = res["results"][0].get("raw_content", "")
            if raw_text.strip():
                success = True
                print(f"[{idx}] ✅ Success on attempt {attempt+1}")
                break
        except Exception as e:
            print(
                f"[{idx}] ⚠️ Attempt {attempt+1} failed for {row_data["Nome"]} {row_data["Cognome"]}: {e}"
            )
            sleep_time = rand_gen()
            print(f"Sleeping for {sleep_time} seconds")
            time.sleep(sleep_time)

    # If still no success
    if not success:
        raw_text = "unable to fetch"
        print(f"[{idx}] ❌ Unable to fetch after 3 attempts.")

    # Add new attribute
    row_data["raw_linkedin_total"] = raw_text

    # Append to JSONL immediately
    append_jsonl(row_data, output_path)

    # Optional pause between requests
    sleep_time = rand_gen()
    print(f"Sleeping for {sleep_time} seconds")
    time.sleep(sleep_time)
