"""
Google Search scraper using Serper API.
Searches for Prague tech company websites via targeted queries.
Free tier: 2,500 searches/month at serper.dev
"""

import json
import os
import re
import requests
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

OUTPUT_FILE = Path(__file__).parent.parent / "data" / "raw" / "google_search_companies.json"
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
SERPER_ENDPOINT = "https://google.serper.dev/search"

QUERIES = [
    "tech companies Prague site:.cz",
    "software development company Prague",
    "IT services company Praha Czech Republic",
    "SaaS startup Prague",
    "fintech company Prague",
    "ecommerce tech Prague",
    "cybersecurity company Prague",
    "AI startup Prague",
    "mobile app development Prague",
    "cloud services Prague",
]


def extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return url


def serper_search(query: str, num: int = 10) -> list[dict]:
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": query, "num": num, "gl": "cz", "hl": "en"}

    resp = requests.post(SERPER_ENDPOINT, json=payload, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("organic", []):
        name = item.get("title", "").split(" - ")[0].split(" | ")[0].strip()
        website = item.get("link", "")
        snippet = item.get("snippet", "")

        results.append({
            "name": name,
            "website": website,
            "domain": extract_domain(website),
            "description": snippet,
            "city": "Prague",
            "source": "google_search",
        })

    return results


def scrape_google_search():
    if not SERPER_API_KEY:
        print("ERROR: SERPER_API_KEY not set in .env")
        return []

    all_results = []
    seen_domains = set()

    for query in QUERIES:
        print(f"  Query: {query}")
        try:
            results = serper_search(query, num=10)
            new = [r for r in results if r["domain"] and r["domain"] not in seen_domains]
            seen_domains.update(r["domain"] for r in new)
            all_results.extend(new)
            print(f"    Found {len(new)} new companies (total: {len(all_results)})")
        except Exception as e:
            print(f"    Error: {e}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\nGoogle search scraper done. {len(all_results)} companies saved to {OUTPUT_FILE}")
    return all_results


if __name__ == "__main__":
    scrape_google_search()
