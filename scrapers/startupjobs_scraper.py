"""
Scraper for startupjobs.cz/firmy — Czech startup company directory.
Uses ScrapeGraphAI (SmartScraperMultiGraph) with Groq as the LLM.
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
from scrapegraphai.graphs import SmartScraperGraph

load_dotenv()

OUTPUT_FILE = Path(__file__).parent.parent / "data" / "raw" / "startupjobs_companies.json"

# Pages to scrape (startupjobs.cz paginates company listings)
BASE_URLS = [f"https://www.startupjobs.cz/firmy?page={i}" for i in range(1, 16)]

GRAPH_CONFIG = {
    "llm": {
        "model": "groq/llama3-70b-8192",
        "api_key": os.getenv("GROQ_API_KEY"),
    },
    "verbose": False,
    "headless": True,
}

PROMPT = """
Extract all company listings from this page.
For each company return:
- name: company name
- website: company website URL (if shown)
- size: employee count or range (e.g. "10-50", "50-200")
- tech_stack: list of technologies mentioned (if any)
- city: office city (look for Prague / Praha)
- description: short description (1-2 sentences max)
- source: set to "startupjobs"

Only include companies that have an office in Prague / Praha.
Return a JSON array of objects.
"""


def scrape_startupjobs():
    all_results = []
    seen_names = set()

    for i, url in enumerate(BASE_URLS):
        print(f"  Scraping page {i+1}/{len(BASE_URLS)}: {url}")
        try:
            graph = SmartScraperGraph(
                prompt=PROMPT,
                source=url,
                config=GRAPH_CONFIG,
            )
            result = graph.run()

            # Result may be a list or a dict with a key
            if isinstance(result, list):
                companies = result
            elif isinstance(result, dict):
                companies = next(
                    (v for v in result.values() if isinstance(v, list)), []
                )
            else:
                companies = []

            new = [c for c in companies if c.get("name") and c["name"] not in seen_names]
            seen_names.update(c["name"] for c in new)
            all_results.extend(new)
            print(f"    Found {len(new)} new companies (total: {len(all_results)})")

        except Exception as e:
            print(f"    Error on page {i+1}: {e}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\nStartupjobs scraper done. {len(all_results)} companies saved to {OUTPUT_FILE}")
    return all_results


if __name__ == "__main__":
    scrape_startupjobs()
