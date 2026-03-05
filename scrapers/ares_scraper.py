"""
ARES scraper — Czech official business trade register.
Free REST API, no key required.
Searches NACE codes 58-63 (IT/tech sector) for Praha companies.

API note: obchodniJmeno (name fragment) is required. We cycle through
common tech business name fragments to cover the full company list.
"""

import json
import time
import requests
from pathlib import Path

OUTPUT_FILE = Path(__file__).parent.parent / "data" / "raw" / "ares_companies.json"

ARES_API = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/vyhledat"

# NACE section J = Information and Communication (62 = IT/software is most relevant)
NACE_CODES = ["62", "63", "58", "61", "59", "60"]

# Common fragments in Czech tech company names — cycling gives broad coverage
NAME_FRAGMENTS = [
    "software", "tech", "digital", "data", "cloud", "net", "web",
    "system", "solutions", "services", "consulting", "it ", "app",
    "dev", "code", "smart", "mobile", "platform", "media", "labs",
    "studio", "group", "agency", "innovation", "cyber", "ai",
    "analytics", "security", "automation", "design", "ware",
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k",
    "l", "m", "n", "o", "p", "r", "s", "t", "u", "v", "z",
]

HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}
PAGE_SIZE = 100
MAX_PER_QUERY = 1000


def fetch_ares_page(name_fragment: str, nace: str, start: int = 0) -> dict:
    payload = {
        "pocet": PAGE_SIZE,
        "start": start,
        "obchodniJmeno": name_fragment,
        "sidlo": {"obec": "Praha"},
        "naceKody": [nace],
    }
    resp = requests.post(ARES_API, json=payload, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def scrape_ares():
    all_results = []
    seen_icos = set()

    for nace in NACE_CODES:
        print(f"  NACE {nace} (Prague)...")

        for fragment in NAME_FRAGMENTS:
            start = 0
            while True:
                try:
                    data = fetch_ares_page(fragment, nace, start=start)

                    # Too many results error — skip this fragment
                    if data.get("subKod") == "VYSTUP_PRILIS_MNOHO_VYSLEDKU":
                        break

                    items = data.get("ekonomickeSubjekty", [])
                    if not items:
                        break

                    for item in items:
                        ico = item.get("ico")
                        if not ico or ico in seen_icos:
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
                    start += PAGE_SIZE
                    if start >= total or start >= MAX_PER_QUERY:
                        break

                    time.sleep(0.2)

                except Exception as e:
                    print(f"    Error (NACE {nace}, '{fragment}', start={start}): {e}")
                    break

        print(f"    Running total: {len(all_results)} companies")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\nARES scraper done. {len(all_results)} companies saved to {OUTPUT_FILE}")
    return all_results


if __name__ == "__main__":
    scrape_ares()
