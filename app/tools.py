import re
import tavily


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

