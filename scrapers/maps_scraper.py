"""
Google Maps scraper for Prague tech companies.
Uses Playwright to search Google Maps and extract company data.
"""

import json
import time
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_FILE = Path(__file__).parent.parent / "data" / "raw" / "maps_companies.json"

SEARCH_QUERIES = [
    "tech company Prague",
    "software company Prague",
    "IT company Praha",
    "startup Prague",
    "technology firm Prague",
]


async def scrape_maps_query(page, query: str) -> list[dict]:
    """Scrape a single Google Maps search query."""
    results = []
    url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"

    await page.goto(url, wait_until="networkidle", timeout=30000)
    await page.wait_for_timeout(2000)

    # Scroll the results panel to load more
    for _ in range(8):
        try:
            panel = await page.query_selector('[role="feed"]')
            if panel:
                await panel.evaluate("el => el.scrollTop += 1500")
                await page.wait_for_timeout(1500)
        except Exception:
            break

    # Extract listing cards
    cards = await page.query_selector_all('[jsaction*="mouseover:pane"]')

    for card in cards:
        try:
            name_el = await card.query_selector(".fontHeadlineSmall, .qBF1Pd")
            name = await name_el.inner_text() if name_el else None

            category_el = await card.query_selector(".W4Efsd:nth-child(2) > .W4Efsd > span:first-child")
            category = await category_el.inner_text() if category_el else None

            address_el = await card.query_selector(".W4Efsd:nth-child(2) > .W4Efsd > span:last-child")
            address = await address_el.inner_text() if address_el else None

            if name:
                results.append({
                    "name": name.strip(),
                    "category": category.strip() if category else None,
                    "address": address.strip() if address else None,
                    "city": "Prague",
                    "source": "google_maps",
                })
        except Exception:
            continue

    return results


async def scrape_maps():
    all_results = []
    seen_names = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()

        for query in SEARCH_QUERIES:
            print(f"  Searching: {query}")
            try:
                results = await scrape_maps_query(page, query)
                new = [r for r in results if r["name"] not in seen_names]
                seen_names.update(r["name"] for r in new)
                all_results.extend(new)
                print(f"    Found {len(new)} new companies (total: {len(all_results)})")
            except Exception as e:
                print(f"    Error on '{query}': {e}")
            time.sleep(1)

        await browser.close()

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\nMaps scraper done. {len(all_results)} companies saved to {OUTPUT_FILE}")
    return all_results


if __name__ == "__main__":
    asyncio.run(scrape_maps())
