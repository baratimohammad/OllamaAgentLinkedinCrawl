import os
import json
import time
import random
import pandas as pd
from tavily import TavilyClient


class LinkedinExtractor:
    def __init__(self, input_path, output_path, sheet_name="students_linkedin_20230504"):
        self.input_path = input_path
        self.output_path = output_path
        self.sheet_name = sheet_name
        self.tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        
        print("✅ Tavily client initiated")

        self.df = self._load_excel()
        self.processed_urls = self._load_processed_urls()

    # === Internal utilities ===
    def _load_excel(self):
        df = pd.read_excel(self.input_path, sheet_name=self.sheet_name)

    # Handle both "LinkedIn" and "LINKEDIN" column names
        if "LinkedIn" in df.columns:
            linkedin_col = "LinkedIn"
        elif "LINKEDIN" in df.columns:
            linkedin_col = "LINKEDIN"
            # Rename it for consistency with the rest of your pipeline
            df.rename(columns={"LINKEDIN": "LinkedIn"}, inplace=True)
        else:
            raise ValueError("❌ Missing required column: 'LinkedIn' or 'LINKEDIN'")

        # Drop rows with missing LinkedIn values
        df = df.dropna(subset=["LinkedIn"])
        print(f"📘 Loaded {len(df)} rows to process.")
        return df

    def _load_processed_urls(self):
        processed = set()
        if os.path.exists(self.output_path):
            print("🔍 Checking for already processed records...")
            with open(self.output_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        url = str(record.get("LinkedIn", "")).strip()
                        if url:
                            processed.add(url)
                    except json.JSONDecodeError:
                        continue
            print(f"✅ Found {len(processed)} processed records.")
        else:
            print("🆕 No existing output file found; starting fresh.")
        return processed

    def _append_jsonl(self, record):
        with open(self.output_path, "a", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False)
            f.write("\n")

    def _rand_sleep(self):
        r1 = random.uniform(0, 10)
        r2 = random.uniform(5, 15)
        if r1 < r2:
            r3 = random.uniform(r1, r2)
        elif r2 < r1:
            r3 = random.uniform(r2, r1)
        else:
            r3 = r1
        return r3

    # === Core function ===
    def process(self):
        for idx, row in self.df.iterrows():
            url = str(row["LinkedIn"]).strip()
            row_data = row.to_dict()

            # Check if already processed
            if url in self.processed_urls:
                print(f"[{idx}] ⏭️ Skipping already processed: {url}")
                continue

            # If invalid or missing URL → record nulls
            if not url or not ("linkedin.com" in url):
                print(f"[{idx}] ⚠️ Invalid or missing URL: {url}")
                row_data["raw_linkedin_total"] = "invalid or missing URL"
                row_data["extraction_time_sec"] = None
                self._append_jsonl(row_data)
                self.processed_urls.add(url)
                continue

            # Valid URL → proceed with extraction
            print(f"[{idx}] 🔍 Extracting {url} ...")

            start_time = time.time()
            raw_text = self._extract_raw_text(url, row_data)
            elapsed = round(time.time() - start_time, 2)

            row_data["raw_linkedin_total"] = raw_text
            row_data["extraction_time_sec"] = elapsed

            self._append_jsonl(row_data)
            self.processed_urls.add(url)

            print(f"[{idx}] ⏱️ Extraction took {elapsed} seconds")

            sleep_time = self._rand_sleep()
            print(f"💤 Sleeping for {sleep_time:.1f} seconds")
            time.sleep(sleep_time)

        print("🎉 Processing complete.")

    def _extract_raw_text(self, url, row_data):
        """Handles retries + extraction logic"""
        raw_text = ""
        trials = 10
        for attempt in range(trials):
            try:
                res = self.tavily.extract(urls=[url], extract_depth = "advanced")
                if res.get("results"):
                    raw_text = res["results"][0].get("raw_content", "")
                if raw_text.strip():
                    print(f"✅ Success on attempt {attempt + 1}")
                    return raw_text
            except Exception as e:
                print(
                    f"⚠️ Attempt {attempt + 1} failed for "
                    f"{row_data.get('Nome')} {row_data.get('Cognome')}: {e}"
                )
                sleep_time = self._rand_sleep()
                print(f"Sleeping for {sleep_time:.1f} seconds")
                time.sleep(sleep_time)

        print(f"❌ Unable to fetch after {trials} attempts.")
        return "unable to fetch"


if __name__ == "__main__":
    input_path = "shared_data/linkedininput/students_linkedin_20230504.xlsx"
    output_path = "shared_data/linkedinoutput/bronze/raw_linkedin_total.jsonl"

    extractor = LinkedinExtractor(
        input_path=input_path,
        output_path=output_path,
        sheet_name="students_linkedin_20230504",
    )
    extractor.process()

    input_path = "shared_data/linkedininput/profili_google_Linkedin_40_ciclo_rev.xlsx"

    extractor = LinkedinExtractor(
        input_path=input_path,
        output_path=output_path,
        sheet_name="40th cycle + cotutelle 39th",
    )
    extractor.process()