"""
Job checker — for each company, checks if they have active job listings
for Product Manager, Product Designer, UX Designer, or UX Researcher in Prague.

Uses Serper API for general companies.
For startupjobs.cz companies, checks that platform directly first.

Adds columns: product_jobs, design_jobs, ux_jobs (1/0)
"""

import json
import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

INPUT_FILE = Path(__file__).parent.parent / "data" / "raw" / "deduped.json"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "raw" / "with_jobs.json"

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
SERPER_ENDPOINT = "https://google.serper.dev/search"

PRODUCT_TERMS = ["Product Manager", "Product Owner", "Head of Product"]
DESIGN_TERMS = ["Product Designer", "UI Designer", "Visual Designer"]
UX_TERMS = ["UX Designer", "UX Researcher", "User Experience", "UX Lead"]


def serper_job_search(company_name: str, terms: list[str]) -> bool:
    """Return True if any of the terms appear in job listings for this company."""
    query_terms = " OR ".join(f'"{t}"' for t in terms)
    query = f'"{company_name}" ({query_terms}) Prague job'

    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": query, "num": 5, "gl": "cz"}

    try:
        resp = requests.post(SERPER_ENDPOINT, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return len(data.get("organic", [])) > 0
    except Exception:
        return False


def check_startupjobs(company_name: str) -> tuple[bool, bool, bool]:
    """Check startupjobs.cz directly for Product/Design/UX listings."""
    try:
        url = f"https://www.startupjobs.cz/nabidky?q={requests.utils.quote(company_name)}"
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        text = resp.text.lower()
        product = any(t.lower() in text for t in PRODUCT_TERMS)
        design = any(t.lower() in text for t in DESIGN_TERMS)
        ux = any(t.lower() in text for t in UX_TERMS)
        return product, design, ux
    except Exception:
        return False, False, False


def check_jobs(records: list[dict]) -> list[dict]:
    if not SERPER_API_KEY:
        print("WARNING: SERPER_API_KEY not set — skipping job check, all columns will be 0")
        for r in records:
            r["product_jobs"] = 0
            r["design_jobs"] = 0
            r["ux_jobs"] = 0
        return records

    total = len(records)
    for i, rec in enumerate(records):
        name = rec.get("name", "")
        source = rec.get("source", "")
        print(f"  [{i+1}/{total}] Checking: {name}")

        if "startupjobs" in source:
            product, design, ux = check_startupjobs(name)
        else:
            product = serper_job_search(name, PRODUCT_TERMS)
            time.sleep(0.2)
            design = serper_job_search(name, DESIGN_TERMS)
            time.sleep(0.2)
            ux = serper_job_search(name, UX_TERMS)
            time.sleep(0.2)

        rec["product_jobs"] = 1 if product else 0
        rec["design_jobs"] = 1 if design else 0
        rec["ux_jobs"] = 1 if ux else 0

    return records


def run_job_checker():
    with open(INPUT_FILE, encoding="utf-8") as f:
        records = json.load(f)

    print(f"Checking jobs for {len(records)} companies...")
    records = check_jobs(records)

    hiring_count = sum(1 for r in records if r["product_jobs"] or r["design_jobs"] or r["ux_jobs"])
    print(f"\n{hiring_count} companies have matching job listings")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"Saved to {OUTPUT_FILE}")
    return records


if __name__ == "__main__":
    run_job_checker()
