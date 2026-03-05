# Tech-Search-2026

A database of 300+ Prague tech companies built for job outreach — scraped from 7 sources, deduped, and exported to Google Sheets with outreach tracking columns.

## What it does

1. Scrapes company data from Google Maps, StartupJobs.cz, ARES (Czech trade register), Google Search, Crunchbase, Dealroom, and LinkedIn
2. Merges and deduplicates everything by website domain
3. Checks each company for active Product / Design / UX job listings
4. Exports to `data/final_companies.csv` and Google Sheets

## Setup

**1. Install dependencies**
```bash
pip install -r requirements.txt
playwright install chromium
```

**2. Create your `.env` file**
```bash
cp .env.example .env
# Then edit .env and fill in your API keys
```

Get free keys:
- **GROQ_API_KEY** at console.groq.com
- **SERPER_API_KEY** at serper.dev (2,500 free searches/month)

**3. Run everything**
```bash
python run_all.py
```

Or run individual scrapers:
```bash
python scrapers/ares_scraper.py       # Czech trade register (no API key needed)
python scrapers/maps_scraper.py       # Google Maps
python scrapers/startupjobs_scraper.py
python scrapers/google_search_scraper.py
python scrapers/crunchbase_scraper.py
python scrapers/dealroom_scraper.py
python scrapers/linkedin_scraper.py
```

Then run the pipeline:
```bash
python pipeline/merge.py
python pipeline/deduplicate.py
python pipeline/job_checker.py
python pipeline/export.py
```

## Output columns

| Column | Description |
|--------|-------------|
| Company Name | Company name |
| Website | Website URL |
| Size | Employee count/range |
| Industry | Sector/category |
| City | City (Prague) |
| Address | Street address |
| Phone | Phone number |
| Product | 1 if hiring Product Manager/Owner |
| Design | 1 if hiring Product/UI Designer |
| UX | 1 if hiring UX Designer/Researcher |
| Source | Which scraper(s) found this company |
| Notes | Manual notes |

Plus outreach tracking columns in Google Sheets: **Contacted / Date Contacted / Response / Portfolio Sent / Follow Up Date**

## Flags

```bash
python run_all.py --skip-scrapers   # Re-run pipeline only (raw data already exists)
python run_all.py --skip-jobs       # Skip job-checking (saves ~300 Serper API calls)
```
