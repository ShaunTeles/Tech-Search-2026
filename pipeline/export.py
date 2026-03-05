"""
Export final data to:
1. data/final_companies.csv  — backup CSV
2. Google Sheets — for outreach tracking

Google Sheets uses gspread with OAuth credentials from google-workspace MCP.
"""

import csv
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

INPUT_FILE = Path(__file__).parent.parent / "data" / "raw" / "with_jobs.json"
CSV_OUTPUT = Path(__file__).parent.parent / "data" / "final_companies.csv"

# Column order for CSV and Google Sheets
DATA_COLUMNS = [
    "name",
    "website",
    "size",
    "industry",
    "city",
    "address",
    "phone",
    "product_jobs",
    "design_jobs",
    "ux_jobs",
    "source",
    "notes",
]

# Outreach tracking columns — added to Google Sheets but left blank
OUTREACH_COLUMNS = [
    "Contacted",
    "Date Contacted",
    "Response",
    "Portfolio Sent",
    "Follow Up Date",
]

SHEET_NAME = "Prague Tech Companies"


def load_records() -> list[dict]:
    with open(INPUT_FILE, encoding="utf-8") as f:
        records = json.load(f)
    # Ensure all columns exist
    for rec in records:
        for col in DATA_COLUMNS:
            if col not in rec:
                rec[col] = ""
    return records


def export_csv(records: list[dict]):
    with open(CSV_OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DATA_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    print(f"CSV saved: {CSV_OUTPUT} ({len(records)} rows)")


def export_google_sheets(records: list[dict]):
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        print("gspread not installed — skipping Google Sheets export")
        print("Run: pip install gspread google-auth")
        return

    # Look for service account credentials
    creds_path = Path.home() / ".config" / "gspread" / "credentials.json"
    service_account_path = Path.home() / ".config" / "gspread" / "service_account.json"

    try:
        if service_account_path.exists():
            gc = gspread.service_account(filename=str(service_account_path))
        else:
            # gspread 6.x: oauth() auto-reads from ~/.config/gspread/credentials.json
            gc = gspread.oauth()

        # Create or open sheet
        try:
            sh = gc.open(SHEET_NAME)
            worksheet = sh.sheet1
            print(f"Opened existing sheet: {SHEET_NAME}")
        except gspread.SpreadsheetNotFound:
            sh = gc.create(SHEET_NAME)
            worksheet = sh.sheet1
            print(f"Created new sheet: {SHEET_NAME}")

        # Build header row
        all_columns = DATA_COLUMNS + OUTREACH_COLUMNS
        header = [c.replace("_", " ").title() for c in DATA_COLUMNS] + OUTREACH_COLUMNS

        # Build data rows
        rows = [header]
        for rec in records:
            row = [rec.get(col, "") for col in DATA_COLUMNS] + [""] * len(OUTREACH_COLUMNS)
            rows.append(row)

        # Clear and write
        worksheet.clear()
        worksheet.update(rows, value_input_option="USER_ENTERED")

        print(f"Google Sheets updated: {len(records)} rows + {len(OUTREACH_COLUMNS)} outreach columns")
        print(f"Sheet URL: {sh.url}")

    except Exception as e:
        print(f"Google Sheets export failed: {e}")
        print("Check your gspread credentials. CSV export still succeeded.")


def run_export():
    print("Loading final records...")
    records = load_records()
    print(f"Exporting {len(records)} companies...")

    export_csv(records)
    export_google_sheets(records)

    print("\nExport complete.")


if __name__ == "__main__":
    run_export()
