general_prompt = f"""
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

