"""
Scraper for startupjobs.cz — uses their internal API directly.
No browser needed — pure HTTP requests.
~3,800+ companies across 214 pages.
"""

import json
import time
import requests
from pathlib import Path

OUTPUT_FILE = Path(__file__).parent.parent / "data" / "raw" / "startupjobs_companies.json"

API_URL = "https://www.startupjobs.cz/api/front/companies"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://www.startupjobs.cz/firmy",
}
MAX_PAGES = 220


def fetch_page(page_num: int) -> list[dict]:
    params = {"page": page_num, "followedOnly": "false"}
    resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()


def scrape_startupjobs() -> list[dict]:
    all_results = []
    seen_ids = set()

    for page_num in range(1, MAX_PAGES + 1):
        try:
            items = fetch_page(page_num)
            if not items:
                print(f"  Page {page_num}: empty — done")
                break

            new = []
            for item in items:
                company_id = item.get("id")
                if company_id in seen_ids:
                    continue
                seen_ids.add(company_id)

                slug = item.get("slug", "")
                new.append({
                    "name": item.get("name"),
                    "description": item.get("introduction") or item.get("introduction_en"),
                    "industry": item.get("area", {}).get("en") or item.get("area", {}).get("cs"),
                    "startupjobs_url": f"https://www.startupjobs.cz/startup/{slug}" if slug else None,
                    "city": "Prague",
                    "source": "startupjobs",
                })

            all_results.extend(new)
            if page_num % 20 == 0 or page_num == 1:
                print(f"  Page {page_num}: +{len(new)} companies (total: {len(all_results)})")

            time.sleep(0.15)  # polite delay

        except Exception as e:
            print(f"  Error on page {page_num}: {e}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\nStartupJobs scraper done. {len(all_results)} companies saved to {OUTPUT_FILE}")
    return all_results


if __name__ == "__main__":
    scrape_startupjobs()
