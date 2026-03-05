"""
ARES scraper — Czech official business trade register.
Free REST API, no key required.
Queries NACE code section J (Information and Communication) for Praha.
Docs: https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/
"""

import json
import time
import requests
from pathlib import Path

OUTPUT_FILE = Path(__file__).parent.parent / "data" / "raw" / "ares_companies.json"

ARES_API = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/vyhledat"

# NACE section J = Information and Communication
# Subsections: 58-63 (publishing, telecom, IT, data processing, etc.)
NACE_CODES = ["58", "59", "60", "61", "62", "63"]

HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


def fetch_ares_page(nace_prefix: str, start: int = 0, size: int = 100) -> dict:
    payload = {
        "pocet": size,
        "start": start,
        "obec": "Praha",
        "naceKod": nace_prefix,
        "jenAktivni": True,
    }
    resp = requests.post(ARES_API, json=payload, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def scrape_ares():
    all_results = []
    seen_icos = set()

    for nace in NACE_CODES:
        print(f"  NACE {nace}x (Prague)...")
        start = 0
        page_size = 100

        while True:
            try:
                data = fetch_ares_page(nace, start=start, size=page_size)
                items = data.get("ekonomickeSubjekty", [])

                if not items:
                    break

                for item in items:
                    ico = item.get("ico")
                    if ico in seen_icos:
                        continue
                    seen_icos.add(ico)

                    address = item.get("sidlo", {})
                    all_results.append({
                        "name": item.get("obchodniJmeno"),
                        "ico": ico,
                        "address": address.get("textovaAdresa"),
                        "city": "Prague",
                        "nace": nace,
                        "source": "ares",
                    })

                total = data.get("pocetCelkem", 0)
                start += page_size
                if start >= total or start >= 500:  # cap at 500 per NACE
                    break

                time.sleep(0.3)  # be polite to the API

            except Exception as e:
                print(f"    Error at NACE {nace} start={start}: {e}")
                break

        print(f"    Running total: {len(all_results)} companies")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\nARES scraper done. {len(all_results)} companies saved to {OUTPUT_FILE}")
    return all_results


if __name__ == "__main__":
    scrape_ares()
