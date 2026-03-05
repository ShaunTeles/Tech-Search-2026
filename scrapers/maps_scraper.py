"""
Google Maps scraper for Prague tech companies.
Uses Playwright with cookie consent handling.
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
    "fintech Prague",
    "SaaS company Prague",
    "cybersecurity Prague",
    "AI company Prague",
]


async def accept_cookies(page):
    try:
        btn = await page.query_selector('button[aria-label*="Accept"], form[action*="consent"] button:last-child')
        if btn:
            await btn.click()
            await page.wait_for_timeout(3000)
    except Exception:
        pass


async def scrape_maps_query(page, query: str, cookies_accepted: bool) -> tuple[list[dict], bool]:
    url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(3000)

    if not cookies_accepted:
        await accept_cookies(page)
        cookies_accepted = True
        await page.wait_for_timeout(2000)

    # Scroll the results panel to load more
    panel = await page.query_selector('[role="feed"]')
    if panel:
        for _ in range(10):
            await panel.evaluate("el => el.scrollTop += 1500")
            await page.wait_for_timeout(800)

    # Extract place links — aria-label contains the company name
    links = await page.query_selector_all('a[href*="/maps/place"]')
    results = []
    for link in links:
        try:
            name = await link.get_attribute("aria-label")
            href = await link.get_attribute("href")
            if name and name.strip():
                results.append({
                    "name": name.strip(),
                    "maps_url": href,
                    "city": "Prague",
                    "source": "google_maps",
                })
        except Exception:
            continue

    return results, cookies_accepted


async def scrape_maps():
    all_results = []
    seen_names = set()
    cookies_accepted = False

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
        )
        page = await context.new_page()

        for query in SEARCH_QUERIES:
            print(f"  Searching: {query}")
            try:
                results, cookies_accepted = await scrape_maps_query(page, query, cookies_accepted)
                new = [r for r in results if r["name"] not in seen_names]
                seen_names.update(r["name"] for r in new)
                all_results.extend(new)
                print(f"    Found {len(results)} entries, {len(new)} new (total: {len(all_results)})")
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
