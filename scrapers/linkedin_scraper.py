"""
LinkedIn scraper using ScrapeGraphAI — targeted search pages only.
LinkedIn blocks mass crawling, so we only target public search result pages.
This is intentionally conservative to avoid IP blocks.
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
from scrapegraphai.graphs import SmartScraperGraph

load_dotenv()

OUTPUT_FILE = Path(__file__).parent.parent / "data" / "raw" / "linkedin_companies.json"

# Targeted public LinkedIn search pages for Prague tech companies
URLS = [
    "https://www.linkedin.com/search/results/companies/?keywords=tech%20Prague&origin=GLOBAL_SEARCH_HEADER",
    "https://www.linkedin.com/search/results/companies/?keywords=software%20Praha&origin=GLOBAL_SEARCH_HEADER",
    "https://www.linkedin.com/search/results/companies/?keywords=startup%20Prague%20Czech&origin=GLOBAL_SEARCH_HEADER",
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
Extract all company listings visible on this LinkedIn search results page.
For each company return:
- name: company name
- industry: industry or category shown
- size: employee count or range (if shown)
- city: city (look for Prague / Praha)
- linkedin_url: the LinkedIn company page URL
- source: set to "linkedin"

Only include companies based in Prague / Praha / Czech Republic.
Return a JSON array of objects.
"""


def scrape_linkedin():
    all_results = []
    seen_names = set()

    for url in URLS:
        print(f"  Scraping: {url[:80]}...")
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

            new = [c for c in companies if c.get("name") and c["name"] not in seen_names]
            seen_names.update(c["name"] for c in new)
            all_results.extend(new)
            print(f"    Found {len(new)} new companies (total: {len(all_results)})")

        except Exception as e:
            print(f"    Error: {e}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\nLinkedIn scraper done. {len(all_results)} companies saved to {OUTPUT_FILE}")
    return all_results


if __name__ == "__main__":
    scrape_linkedin()
