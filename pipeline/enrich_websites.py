"""
Enrich company records with website URLs scraped from StartupJobs profiles.
Updates the raw with_jobs.json and regenerates per-source CSVs.
"""

import json
import csv
import re
import time
import requests
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
INPUT_FILE = DATA_DIR / "raw" / "with_jobs.json"
PROGRESS_FILE = DATA_DIR / "raw" / "enrich_progress.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

DATA_COLUMNS = [
    "name", "website", "size", "industry", "city", "address",
    "phone", "product_jobs", "design_jobs", "ux_jobs", "source", "notes",
]


def extract_website_from_profile(html):
    match = re.search(r'"web":\d+[^}]+\},"([^"]+)"', html)
    if match:
        url = match.group(1)
        if not url.startswith("http"):
            url = "https://" + url
        return url
    return None


def enrich_startupjobs_websites(records):
    """Scrape StartupJobs profile pages to get company websites."""
    sj_records = [(i, r) for i, r in enumerate(records)
                  if r.get("startupjobs_url") and not r.get("website")]

    print(f"Enriching websites for {len(sj_records)} StartupJobs companies...")

    # Load progress
    found = 0
    start_from = 0
    if PROGRESS_FILE.exists():
        progress = json.load(open(PROGRESS_FILE))
        start_from = progress.get("enriched", 0)
        records = progress.get("records", records)
        # Recount sj_records
        sj_records = [(i, records[i]) for i, r in enumerate(records)
                      if r.get("startupjobs_url") and not r.get("website")]
        print(f"Resuming from {start_from}")

    for count, (i, rec) in enumerate(sj_records):
        if count < start_from:
            continue

        url = rec["startupjobs_url"]
        name = rec["name"]
        print(f"  [{count+1}/{len(sj_records)}] {name}")

        try:
            resp = requests.get(url, timeout=15, headers=HEADERS)
            if resp.status_code == 200:
                website = extract_website_from_profile(resp.text)
                if website:
                    records[i]["website"] = website
                    found += 1
        except Exception:
            pass

        time.sleep(0.1)

        if (count + 1) % 100 == 0:
            print(f"    [Found {found} websites so far, saving progress...]")
            json.dump({"enriched": count + 1, "records": records},
                      open(PROGRESS_FILE, "w"), ensure_ascii=False)

    # Clean up progress
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()

    print(f"\nFound websites for {found}/{len(sj_records)} companies")
    return records, found


def export_per_source(records):
    """Re-export per-source CSVs with priority-based dedup."""
    priority = ["startupjobs", "google_maps", "google_search", "ares"]
    source_groups = {s: [] for s in priority}

    for rec in records:
        for col in DATA_COLUMNS:
            if col not in rec:
                rec[col] = ""
        source = rec.get("source", "")
        for s in priority:
            if s in source:
                source_groups[s].append(rec)
                break
        else:
            source_groups["ares"].append(rec)

    by_source_dir = DATA_DIR / "by_source"
    by_source_dir.mkdir(exist_ok=True)

    for source_name in priority:
        recs = source_groups[source_name]
        path = by_source_dir / f"final_{source_name}.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=DATA_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(recs)
        has_web = sum(1 for r in recs if r.get("website"))
        print(f"  {path.name}: {len(recs)} companies ({has_web} with website)")


def export_main_csv(records):
    """Re-export the main final_companies.csv."""
    path = DATA_DIR / "final_companies.csv"
    for rec in records:
        for col in DATA_COLUMNS:
            if col not in rec:
                rec[col] = ""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DATA_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    print(f"  final_companies.csv: {len(records)} companies")


def run():
    records = json.load(open(INPUT_FILE, encoding="utf-8"))
    records, found = enrich_startupjobs_websites(records)

    # Save updated JSON
    with open(INPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"Updated {INPUT_FILE}")

    # Re-export CSVs
    print("\nRe-exporting CSVs...")
    export_main_csv(records)
    export_per_source(records)
    print("\nDone!")


if __name__ == "__main__":
    run()
