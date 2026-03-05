"""
Czech tech company scraper using public directories:
- Czech IT Cluster member list
- Praguebest.cz tech companies
- ICT Union member directory

Uses direct HTTP requests + BeautifulSoup.
(Replaces Crunchbase which requires authentication.)
"""

import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup

OUTPUT_FILE = Path(__file__).parent.parent / "data" / "raw" / "crunchbase_companies.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

SOURCES = [
    {
        "url": "https://www.czechitcluster.cz/en/members/",
        "label": "czech_it_cluster",
        "card": "article, .member-item, .views-row, [class*='member'], h2, h3",
        "name_tag": "h2, h3, [class*='title']",
    },
    {
        "url": "https://www.ictunion.cz/clenove/",
        "label": "ict_union",
        "card": "article, .member, li.member",
        "name_tag": "h2, h3, a",
    },
]


def scrape_source(source: dict) -> list[dict]:
    results = []
    try:
        resp = requests.get(source["url"], headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        cards = soup.select(source["card"])
        seen = set()
        for card in cards:
            name_el = card.select_one(source["name_tag"])
            if not name_el:
                continue
            name = name_el.get_text(strip=True)
            if not name or name in seen or len(name) > 100 or len(name) < 2:
                continue
            seen.add(name)

            # Try to find a website link
            link = card.find("a", href=True)
            website = link["href"] if link else None
            if website and (source["label"] in website or website.startswith("/")):
                website = None

            results.append({
                "name": name,
                "website": website,
                "city": "Prague",
                "source": source["label"],
            })

        print(f"  {source['label']}: {len(results)} companies")
    except Exception as e:
        print(f"  {source['label']}: Error — {e}")

    return results


def scrape_crunchbase() -> list[dict]:
    all_results = []
    seen_names = set()

    for source in SOURCES:
        results = scrape_source(source)
        new = [r for r in results if r["name"] not in seen_names]
        seen_names.update(r["name"] for r in new)
        all_results.extend(new)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\nDirectory scraper done. {len(all_results)} companies saved to {OUTPUT_FILE}")
    return all_results


if __name__ == "__main__":
    scrape_crunchbase()
