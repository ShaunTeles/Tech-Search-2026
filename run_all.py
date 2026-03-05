"""
One-command runner: runs all scrapers then the full pipeline.
Usage: python run_all.py

Flags:
  --skip-scrapers   Skip scraping, go straight to pipeline (useful if raw data exists)
  --skip-jobs       Skip job-checking step (faster, no Serper API calls)
"""

import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Prague Tech Company Database — full pipeline")
    parser.add_argument("--skip-scrapers", action="store_true", help="Skip scraping step")
    parser.add_argument("--skip-jobs", action="store_true", help="Skip job-checking step")
    args = parser.parse_args()

    print("=" * 60)
    print("Prague Tech Company Database — Tech-Search-2026")
    print("=" * 60)

    if not args.skip_scrapers:
        # --- SCRAPERS ---
        print("\n[1/7] Google Maps scraper...")
        try:
            import asyncio
            from scrapers.maps_scraper import scrape_maps
            asyncio.run(scrape_maps())
        except Exception as e:
            print(f"  Maps scraper failed: {e}")

        print("\n[2/7] StartupJobs.cz scraper...")
        try:
            from scrapers.startupjobs_scraper import scrape_startupjobs
            scrape_startupjobs()
        except Exception as e:
            print(f"  StartupJobs scraper failed: {e}")

        print("\n[3/7] ARES (Czech trade register)...")
        try:
            from scrapers.ares_scraper import scrape_ares
            scrape_ares()
        except Exception as e:
            print(f"  ARES scraper failed: {e}")

        print("\n[4/7] Google Search (Serper API)...")
        try:
            from scrapers.google_search_scraper import scrape_google_search
            scrape_google_search()
        except Exception as e:
            print(f"  Google Search scraper failed: {e}")

        print("\n[5/7] Crunchbase scraper...")
        try:
            from scrapers.crunchbase_scraper import scrape_crunchbase
            scrape_crunchbase()
        except Exception as e:
            print(f"  Crunchbase scraper failed: {e}")

        print("\n[6/7] Dealroom + Startup Blink scraper...")
        try:
            from scrapers.dealroom_scraper import scrape_dealroom
            scrape_dealroom()
        except Exception as e:
            print(f"  Dealroom scraper failed: {e}")

        print("\n[7/7] LinkedIn scraper...")
        try:
            from scrapers.linkedin_scraper import scrape_linkedin
            scrape_linkedin()
        except Exception as e:
            print(f"  LinkedIn scraper failed: {e}")

    # --- PIPELINE ---
    print("\n[Pipeline 1/4] Merging raw data...")
    try:
        from pipeline.merge import merge
        records = merge()
    except Exception as e:
        print(f"  Merge failed: {e}")
        sys.exit(1)

    print("\n[Pipeline 2/4] Deduplicating...")
    try:
        from pipeline.deduplicate import deduplicate
        records = deduplicate()
    except Exception as e:
        print(f"  Dedup failed: {e}")
        sys.exit(1)

    if not args.skip_jobs:
        print("\n[Pipeline 3/4] Checking job listings...")
        try:
            from pipeline.job_checker import run_job_checker
            records = run_job_checker()
        except Exception as e:
            print(f"  Job checker failed: {e}")
    else:
        print("\n[Pipeline 3/4] Skipping job check (--skip-jobs)")
        import json
        from pathlib import Path
        deduped = Path("data/raw/deduped.json")
        with_jobs = Path("data/raw/with_jobs.json")
        data = json.loads(deduped.read_text())
        for r in data:
            r.setdefault("product_jobs", 0)
            r.setdefault("design_jobs", 0)
            r.setdefault("ux_jobs", 0)
        with_jobs.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    print("\n[Pipeline 4/4] Exporting to CSV + Google Sheets...")
    try:
        from pipeline.export import run_export
        run_export()
    except Exception as e:
        print(f"  Export failed: {e}")

    print("\n" + "=" * 60)
    print("Done! Check data/final_companies.csv")
    print("=" * 60)


if __name__ == "__main__":
    main()
