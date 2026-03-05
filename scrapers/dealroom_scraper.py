"""
Scraper for Czech startup ecosystem directories:
- czechstartups.org
- CzechInvest tech company listings
- Jobstack.cz company directory
Uses direct Playwright scraping.
"""

import json
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_FILE = Path(__file__).parent.parent / "data" / "raw" / "dealroom_companies.json"

SOURCES = [
    {
        "url": "https://www.czechstartups.org/en/startups/",
        "label": "czechstartups",
        "card_selector": "article, .startup-item, [class*='startup'], [class*='company']",
        "name_selector": "h2, h3, [class*='title'], [class*='name']",
    },
    {
        "url": "https://www.jobstack.cz/en/companies",
        "label": "jobstack",
        "card_selector": "a[href*='/companies/'], [class*='company-card'], article",
        "name_selector": "h2, h3, [class*='name'], [class*='title']",
    },
]


async def scrape_source(page, source: dict) -> list[dict]:
    results = []
    print(f"  Scraping {source['label']}: {source['url']}")
    try:
        await page.goto(source["url"], wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        # Scroll to load more content
        for _ in range(5):
            await page.evaluate("window.scrollBy(0, 1500)")
            await page.wait_for_timeout(800)

        cards = await page.query_selector_all(source["card_selector"])
        print(f"    Found {len(cards)} cards")

        seen = set()
        for card in cards:
            try:
                name_el = await card.query_selector(source["name_selector"])
                if not name_el:
                    continue
                name = (await name_el.inner_text()).strip()
                if not name or name in seen or len(name) > 100:
                    continue
                seen.add(name)

                # Try to get website link
                link = await card.query_selector("a[href*='http']")
                website = await link.get_attribute("href") if link else None
                if website and source["label"] in website:
                    website = None  # skip internal links

                results.append({
                    "name": name,
                    "website": website,
                    "city": "Prague",
                    "source": source["label"],
                })
            except Exception:
                continue

    except Exception as e:
        print(f"    Error: {e}")

    print(f"    Extracted {len(results)} companies from {source['label']}")
    return results


async def scrape_dealroom():
    all_results = []
    seen_names = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for source in SOURCES:
            results = await scrape_source(page, source)
            new = [r for r in results if r["name"] not in seen_names]
            seen_names.update(r["name"] for r in new)
            all_results.extend(new)

        await browser.close()

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\nDealroom/directories scraper done. {len(all_results)} companies saved to {OUTPUT_FILE}")
    return all_results


if __name__ == "__main__":
    asyncio.run(scrape_dealroom())
