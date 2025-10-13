import pandas as pd

import pandas as pd
from tavily import TavilyClient
import os
import json
import time
import random


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


tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
print("Tavily client initiated")

url = "https://www.linkedin.com/in/mleogrande/"

for attempt in range(3):
    try:
        res = tavily.extract(urls=[url])
        if res.get("results"):
            raw_text = res["results"][0].get("raw_content", "")
        if raw_text.strip():
            success = True
            print(f"✅ Success on attempt {attempt+1}")
            break
    except Exception as e:
        print(
            f"⚠️ Attempt {attempt+1} failed for: {e}"
        )
    sleep_time = rand_gen()
    print(f"Sleeping for {sleep_time} seconds")
    time.sleep(sleep_time)