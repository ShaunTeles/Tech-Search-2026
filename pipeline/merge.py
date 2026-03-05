"""
Merge all scraper outputs into a single combined JSON file.
Reads from data/raw/*.json and outputs data/raw/merged.json
"""

import json
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_FILE = RAW_DIR / "merged.json"

# Field normalisation map: scraper-specific field -> canonical field
FIELD_MAP = {
    "company_name": "name",
    "companyName": "name",
    "url": "website",
    "web": "website",
    "homepage": "website",
    "employees": "size",
    "employee_count": "size",
    "sector": "industry",
    "category": "industry",
    "town": "city",
    "location": "city",
    "textovaAdresa": "address",
}


def normalise(record: dict) -> dict:
    """Rename non-standard fields to canonical names."""
    out = {}
    for k, v in record.items():
        canonical = FIELD_MAP.get(k, k)
        out[canonical] = v
    return out


def load_raw_files() -> list[dict]:
    all_records = []
    files = sorted(RAW_DIR.glob("*.json"))
    files = [f for f in files if f.name != "merged.json"]

    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, list):
                print(f"  Skipping {f.name} — not a list")
                continue
            normalised = [normalise(r) for r in data]
            all_records.extend(normalised)
            print(f"  Loaded {len(data)} records from {f.name}")
        except Exception as e:
            print(f"  Error loading {f.name}: {e}")

    return all_records


def merge():
    print("Merging raw scraper outputs...")
    records = load_raw_files()
    print(f"\nTotal before dedup: {len(records)} records")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"Saved merged data to {OUTPUT_FILE}")
    return records


if __name__ == "__main__":
    merge()
