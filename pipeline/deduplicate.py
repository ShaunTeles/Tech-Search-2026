"""
Deduplicate merged company records.
Primary key: normalised website domain.
Secondary key: normalised company name (fuzzy, for records without a website).
Outputs data/raw/deduped.json
"""

import json
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

INPUT_FILE = Path(__file__).parent.parent / "data" / "raw" / "merged.json"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "raw" / "deduped.json"


def normalise_domain(url: str) -> Optional[str]:
    if not url:
        return None
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    try:
        domain = urlparse(url).netloc.lower().replace("www.", "").strip("/")
        return domain if domain else None
    except Exception:
        return None


def normalise_name(name: str) -> str:
    if not name:
        return ""
    return re.sub(r"[^a-z0-9]", "", name.lower().strip())


def merge_records(existing: dict, new: dict) -> dict:
    """Fill in missing fields from a duplicate record."""
    merged = dict(existing)
    for k, v in new.items():
        if v and not merged.get(k):
            merged[k] = v
    # Combine sources
    sources = set()
    for s in [existing.get("source", ""), new.get("source", "")]:
        if s:
            sources.update(s.split(","))
    merged["source"] = ",".join(sorted(sources))
    return merged


def deduplicate():
    with open(INPUT_FILE, encoding="utf-8") as f:
        records = json.load(f)

    print(f"Input: {len(records)} records")

    by_domain: dict[str, dict] = {}
    by_name: dict[str, dict] = {}
    no_key: list[dict] = []

    for rec in records:
        domain = normalise_domain(rec.get("website"))
        name_key = normalise_name(rec.get("name"))

        if domain:
            if domain in by_domain:
                by_domain[domain] = merge_records(by_domain[domain], rec)
            else:
                by_domain[domain] = rec
        elif name_key:
            if name_key in by_name:
                by_name[name_key] = merge_records(by_name[name_key], rec)
            else:
                by_name[name_key] = rec
        else:
            no_key.append(rec)

    # Also check name-keyed records against domain-keyed ones
    final = list(by_domain.values())
    existing_names = {normalise_name(r.get("name", "")) for r in final}

    for name_key, rec in by_name.items():
        if name_key not in existing_names:
            final.append(rec)

    # Filter out records with no name
    final = [r for r in final if r.get("name")]

    print(f"Output: {len(final)} unique companies (removed {len(records) - len(final)} duplicates)")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    print(f"Saved to {OUTPUT_FILE}")
    return final


if __name__ == "__main__":
    deduplicate()
