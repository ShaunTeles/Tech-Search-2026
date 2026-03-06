"""
Job checker — 3-step strategy to check companies for active job listings
in Product, Design, UX, User, and User Experience roles in Prague.

Step 1: StartupJobs companies — scrape their profile pages directly (FREE)
Step 2: Companies with websites — check career pages directly (FREE)
Step 3: Remaining companies — Serper API with rotating keys (3 keys)

Adds columns: product_jobs, design_jobs, ux_jobs (1/0)
"""

import json
import os
import time
import requests
from pathlib import Path
from urllib.parse import urljoin
from dotenv import load_dotenv

load_dotenv()

INPUT_FILE = Path(__file__).parent.parent / "data" / "raw" / "deduped.json"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "raw" / "with_jobs.json"
PROGRESS_FILE = Path(__file__).parent.parent / "data" / "raw" / "job_check_progress.json"

SERPER_ENDPOINT = "https://google.serper.dev/search"

PRODUCT_TERMS = ["product manager", "product owner", "head of product"]
DESIGN_TERMS = ["product designer", "ui designer", "visual designer"]
UX_TERMS = ["ux designer", "ux researcher", "user experience", "ux lead", "user research"]

ALL_KEYWORDS = PRODUCT_TERMS + DESIGN_TERMS + UX_TERMS

CAREER_PATHS = [
    "/careers", "/jobs", "/kariera", "/volna-mista", "/open-positions",
    "/career", "/hiring", "/join-us", "/join", "/work-with-us",
    "/pracovni-nabidky", "/nabidky-prace",
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def load_serper_keys():
    keys = []
    # Check for base key (SERPER_API_KEY) and numbered keys (_1 through _9)
    base_key = os.getenv("SERPER_API_KEY")
    if base_key:
        keys.append(base_key)
    for i in range(1, 10):
        key = os.getenv(f"SERPER_API_KEY_{i}")
        if key and key not in keys:
            keys.append(key)
    return keys


def classify_hit(text):
    text = text.lower()
    product = any(t in text for t in PRODUCT_TERMS)
    design = any(t in text for t in DESIGN_TERMS)
    ux = any(t in text for t in UX_TERMS)
    return product, design, ux


# --- STEP 1: StartupJobs profile scraping (FREE) ---

def check_startupjobs_profile(url):
    try:
        resp = requests.get(url, timeout=15, headers=HEADERS)
        if resp.status_code != 200:
            return False, False, False
        return classify_hit(resp.text)
    except Exception:
        return False, False, False


# --- STEP 2: Career page scraping (FREE) ---

def check_career_pages(website):
    if not website:
        return None
    base = website.rstrip("/")
    if not base.startswith("http"):
        base = "https://" + base

    for path in CAREER_PATHS:
        url = base + path
        try:
            resp = requests.get(url, timeout=10, headers=HEADERS, allow_redirects=True)
            if resp.status_code == 200 and len(resp.text) > 500:
                product, design, ux = classify_hit(resp.text)
                if product or design or ux:
                    return product, design, ux
        except Exception:
            continue

    # Also check the homepage itself
    try:
        resp = requests.get(base, timeout=10, headers=HEADERS, allow_redirects=True)
        if resp.status_code == 200:
            text = resp.text.lower()
            has_career_link = any(kw in text for kw in ["career", "jobs", "kariera", "hiring", "join us"])
            if has_career_link:
                product, design, ux = classify_hit(text)
                if product or design or ux:
                    return product, design, ux
    except Exception:
        pass

    return None  # None means "couldn't determine" — needs Serper fallback


# --- STEP 3: Serper API with key rotation ---

class SerperRotator:
    def __init__(self, keys):
        self.keys = keys
        self.usage = [0] * len(keys)
        self.current = 0
        self.max_per_key = 2500
        self.exhausted = set()

    def get_key(self):
        if len(self.exhausted) >= len(self.keys):
            return None
        while self.current in self.exhausted:
            self.current = (self.current + 1) % len(self.keys)
        return self.keys[self.current]

    def record_use(self):
        self.usage[self.current] += 1
        if self.usage[self.current] >= self.max_per_key:
            self.exhausted.add(self.current)
            self.current = (self.current + 1) % len(self.keys)
        else:
            self.current = (self.current + 1) % len(self.keys)
            while self.current in self.exhausted and len(self.exhausted) < len(self.keys):
                self.current = (self.current + 1) % len(self.keys)

    def record_error(self):
        self.exhausted.add(self.current)
        if len(self.exhausted) < len(self.keys):
            self.current = (self.current + 1) % len(self.keys)
            while self.current in self.exhausted:
                self.current = (self.current + 1) % len(self.keys)

    def remaining(self):
        return sum(self.max_per_key - u for i, u in enumerate(self.usage) if i not in self.exhausted)

    def status(self):
        parts = []
        for i, (k, u) in enumerate(zip(self.keys, self.usage)):
            status = "DONE" if i in self.exhausted else "active"
            parts.append(f"Key {i+1}: {u}/{self.max_per_key} ({status})")
        return " | ".join(parts)


def serper_search(rotator, query):
    key = rotator.get_key()
    if not key:
        return None

    headers = {"X-API-KEY": key, "Content-Type": "application/json"}
    payload = {"q": query, "num": 5, "gl": "cz"}

    try:
        resp = requests.post(SERPER_ENDPOINT, json=payload, headers=headers, timeout=10)
        if resp.status_code == 429 or resp.status_code == 403:
            rotator.record_error()
            return serper_search(rotator, query)
        resp.raise_for_status()
        rotator.record_use()
        data = resp.json()
        return len(data.get("organic", [])) > 0
    except requests.exceptions.HTTPError:
        rotator.record_error()
        return None
    except Exception:
        rotator.record_use()
        return False


def serper_job_check(rotator, company_name):
    product_q = f'"{company_name}" ({" OR ".join(f"{t}" for t in PRODUCT_TERMS)}) Prague job'
    design_q = f'"{company_name}" ({" OR ".join(f"{t}" for t in DESIGN_TERMS)}) Prague job'
    ux_q = f'"{company_name}" ({" OR ".join(f"{t}" for t in UX_TERMS)}) Prague job'

    product = serper_search(rotator, product_q)
    if product is None:
        return None
    time.sleep(0.15)

    design = serper_search(rotator, design_q)
    if design is None:
        return None
    time.sleep(0.15)

    ux = serper_search(rotator, ux_q)
    if ux is None:
        return None
    time.sleep(0.15)

    return product, design, ux


# --- Progress saving/loading for resume support ---

def save_progress(records, checked_count):
    progress = {"checked": checked_count, "records": records}
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False)


def load_progress():
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return None


# --- Main orchestrator ---

def run_job_checker(resume=True):
    with open(INPUT_FILE, encoding="utf-8") as f:
        records = json.load(f)

    total = len(records)

    # Check for resume
    progress = load_progress() if resume else None
    start_from = 0
    if progress and len(progress["records"]) == total:
        start_from = progress["checked"]
        records = progress["records"]
        print(f"Resuming from company {start_from}/{total}")

    # Initialize all records that haven't been checked yet
    for r in records:
        if "product_jobs" not in r:
            r["product_jobs"] = 0
            r["design_jobs"] = 0
            r["ux_jobs"] = 0
            r["job_check_method"] = ""

    # Load Serper keys
    serper_keys = load_serper_keys()
    rotator = SerperRotator(serper_keys) if serper_keys else None
    if serper_keys:
        print(f"Loaded {len(serper_keys)} Serper API keys ({len(serper_keys) * 2500} total searches)")
    else:
        print("WARNING: No Serper API keys found — Step 3 will be skipped")

    # Categorize companies
    startupjobs_idx = []
    website_idx = []
    serper_idx = []

    for i, rec in enumerate(records):
        if i < start_from:
            continue
        if "startupjobs" in rec.get("source", "") and rec.get("startupjobs_url"):
            startupjobs_idx.append(i)
        elif rec.get("website"):
            website_idx.append(i)
        else:
            serper_idx.append(i)

    print(f"\nTotal companies: {total}")
    print(f"Already checked: {start_from}")
    print(f"Step 1 — StartupJobs profiles: {len(startupjobs_idx)}")
    print(f"Step 2 — Career page check: {len(website_idx)}")
    print(f"Step 3 — Serper fallback: {len(serper_idx)}")
    print()

    checked = start_from

    # STEP 1: StartupJobs
    print("=" * 60)
    print("STEP 1: Checking StartupJobs profiles (FREE)")
    print("=" * 60)
    for count, i in enumerate(startupjobs_idx):
        rec = records[i]
        name = rec["name"]
        url = rec["startupjobs_url"]
        print(f"  [{count+1}/{len(startupjobs_idx)}] {name}")

        product, design, ux = check_startupjobs_profile(url)
        rec["product_jobs"] = 1 if product else 0
        rec["design_jobs"] = 1 if design else 0
        rec["ux_jobs"] = 1 if ux else 0
        rec["job_check_method"] = "startupjobs_profile"
        checked += 1

        if (count + 1) % 100 == 0:
            save_progress(records, checked)
            print(f"    [Progress saved: {checked}/{total}]")

        time.sleep(0.1)

    save_progress(records, checked)

    # STEP 2: Career pages
    print()
    print("=" * 60)
    print("STEP 2: Checking career pages (FREE)")
    print("=" * 60)
    need_serper = []
    for count, i in enumerate(website_idx):
        rec = records[i]
        name = rec["name"]
        website = rec.get("website", "")
        print(f"  [{count+1}/{len(website_idx)}] {name} — {website}")

        result = check_career_pages(website)
        if result is not None:
            product, design, ux = result
            rec["product_jobs"] = 1 if product else 0
            rec["design_jobs"] = 1 if design else 0
            rec["ux_jobs"] = 1 if ux else 0
            rec["job_check_method"] = "career_page"
        else:
            need_serper.append(i)
            rec["job_check_method"] = "pending_serper"

        checked += 1
        if (count + 1) % 50 == 0:
            save_progress(records, checked)

    # Add career page failures to serper queue
    serper_idx = need_serper + serper_idx
    save_progress(records, checked)

    # STEP 3: Serper
    print()
    print("=" * 60)
    print(f"STEP 3: Serper API check ({len(serper_idx)} companies)")
    print("=" * 60)

    if not rotator:
        print("No Serper keys — marking remaining companies as unchecked")
        for i in serper_idx:
            records[i]["job_check_method"] = "skipped_no_key"
    else:
        serper_capacity = rotator.remaining() // 3
        if len(serper_idx) > serper_capacity:
            print(f"WARNING: {len(serper_idx)} companies but only enough keys for ~{serper_capacity}")
            print(f"Will check as many as possible before keys run out")

        for count, i in enumerate(serper_idx):
            rec = records[i]
            name = rec["name"]
            print(f"  [{count+1}/{len(serper_idx)}] {name}  |  {rotator.status()}")

            result = serper_job_check(rotator, name)
            if result is None:
                print("\n  All Serper keys exhausted! Stopping Step 3.")
                for j in serper_idx[count:]:
                    records[j]["job_check_method"] = "skipped_keys_exhausted"
                break

            product, design, ux = result
            rec["product_jobs"] = 1 if product else 0
            rec["design_jobs"] = 1 if design else 0
            rec["ux_jobs"] = 1 if ux else 0
            rec["job_check_method"] = "serper"
            checked += 1

            if (count + 1) % 50 == 0:
                save_progress(records, checked)
                print(f"    [Progress saved: {checked}/{total}]")

    save_progress(records, checked)

    # Summary
    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    hiring = sum(1 for r in records if r["product_jobs"] or r["design_jobs"] or r["ux_jobs"])
    methods = {}
    for r in records:
        m = r.get("job_check_method", "unknown")
        methods[m] = methods.get(m, 0) + 1

    print(f"Companies with matching jobs: {hiring}")
    print(f"  Product: {sum(r['product_jobs'] for r in records)}")
    print(f"  Design: {sum(r['design_jobs'] for r in records)}")
    print(f"  UX: {sum(r['ux_jobs'] for r in records)}")
    print(f"\nCheck methods:")
    for m, c in sorted(methods.items(), key=lambda x: -x[1]):
        print(f"  {m}: {c}")

    if rotator:
        print(f"\nSerper usage: {rotator.status()}")

    # Save final output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {OUTPUT_FILE}")

    # Clean up progress file
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()

    return records


if __name__ == "__main__":
    run_job_checker()
