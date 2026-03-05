"""
Scraper for Dealroom.co and Startup Blink — startup ecosystem databases.
Uses ScrapeGraphAI with Groq.
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
from scrapegraphai.graphs import SmartScraperGraph

load_dotenv()

OUTPUT_FILE = Path(__file__).parent.parent / "data" / "raw" / "dealroom_companies.json"

URLS = [
    "https://app.dealroom.co/companies/filter/location/prague",
    "https://www.startupblink.com/startups/czech-republic/prague",
]

GRAPH_CONFIG = {
    "llm": {
        "model": "groq/llama3-70b-8192",
        "api_key": os.getenv("GROQ_API_KEY"),
    },
    "verbose": False,
    "headless": True,
}

PROMPT = """
Extract all company/startup listings visible on this page.
For each company return:
- name: company name
- website: company website URL
- industry: industry or category
- city: city (should be Prague)
- description: short description (1-2 sentences)
- source: set to "dealroom" or "startup_blink" depending on which site this is

Return a JSON array of objects.
"""


def scrape_dealroom():
    all_results = []
    seen_names = set()

    for url in URLS:
        source_label = "dealroom" if "dealroom" in url else "startup_blink"
        print(f"  Scraping {source_label}: {url}")
        try:
            graph = SmartScraperGraph(
                prompt=PROMPT,
                source=url,
                config=GRAPH_CONFIG,
            )
            result = graph.run()

            if isinstance(result, list):
                companies = result
            elif isinstance(result, dict):
                companies = next(
                    (v for v in result.values() if isinstance(v, list)), []
                )
            else:
                companies = []

            # Tag source
            for c in companies:
                c["source"] = source_label

            new = [c for c in companies if c.get("name") and c["name"] not in seen_names]
            seen_names.update(c["name"] for c in new)
            all_results.extend(new)
            print(f"    Found {len(new)} new companies (total: {len(all_results)})")

        except Exception as e:
            print(f"    Error on {source_label}: {e}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\nDealroom scraper done. {len(all_results)} companies saved to {OUTPUT_FILE}")
    return all_results


if __name__ == "__main__":
    scrape_dealroom()
