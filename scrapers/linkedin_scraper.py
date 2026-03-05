"""
Czech tech company scraper using Serper API job search results.
Searches for companies posting jobs in Prague across multiple tech categories.
This replaces LinkedIn scraping (which is blocked without auth).
Uses Serper API — same key as google_search_scraper.py.
"""

import json
import os
import re
import time
import requests
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

OUTPUT_FILE = Path(__file__).parent.parent / "data" / "raw" / "linkedin_companies.json"
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
SERPER_ENDPOINT = "https://google.serper.dev/search"

# Job-specific queries that return Prague company results
QUERIES = [
    "software engineer jobs Prague site:jobs.cz OR site:linkedin.com",
    "product manager jobs Prague Czech tech company",
    "UX designer Prague tech company hiring",
    "backend developer Praha startup hiring",
    "data engineer jobs Prague company",
    "DevOps engineer Prague tech firm",
    "mobile developer Prague company 2024 2025",
    "machine learning engineer Prague hiring",
]


def extract_company_from_result(item: dict) -> dict | None:
    title = item.get("title", "")
    snippet = item.get("snippet", "")
    url = item.get("link", "")

    # Try to extract company name from title — usually "Job Title at Company | ..."
    company = None
    for pattern in [r" at ([^|–\-]+)", r"[\|–\-] ([^|–\-]{3,50})$"]:
        m = re.search(pattern, title)
        if m:
            candidate = m.group(1).strip()
            # Filter out job board names
            if not any(skip in candidate.lower() for skip in ["jobs", "linkedin", "glassdoor", "indeed", "jobs.cz", "startupjobs"]):
                company = candidate
                break

    if not company:
        return None

    domain = urlparse(url).netloc.replace("www.", "") if url else None

    return {
        "name": company,
        "website": None,
        "description": snippet[:200] if snippet else None,
        "city": "Prague",
        "source": "job_search",
    }


def scrape_linkedin() -> list[dict]:
    if not SERPER_API_KEY:
        print("ERROR: SERPER_API_KEY not set in .env")
        return []

    all_results = []
    seen_names = set()

    for query in QUERIES:
        print(f"  Query: {query[:60]}...")
        try:
            headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
            payload = {"q": query, "num": 10, "gl": "cz"}
            resp = requests.post(SERPER_ENDPOINT, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            new_count = 0
            for item in data.get("organic", []):
                company = extract_company_from_result(item)
                if company and company["name"] not in seen_names:
                    seen_names.add(company["name"])
                    all_results.append(company)
                    new_count += 1

            print(f"    +{new_count} companies (total: {len(all_results)})")
            time.sleep(0.3)

        except Exception as e:
            print(f"    Error: {e}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\nJob search scraper done. {len(all_results)} companies saved to {OUTPUT_FILE}")
    return all_results


if __name__ == "__main__":
    scrape_linkedin()
