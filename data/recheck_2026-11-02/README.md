# Listings recheck, 2 November 2026

The `product_jobs`, `design_jobs` and `ux_jobs` flags in `data/final_companies.csv` store no job links, and the Serper step marked a company as hiring whenever a search returned anything. Treat those flags as unreliable.

This recheck looks for real postings with titles and links.

- `db_scan.jsonl`: one line per company with a website (3,813 companies; 392 sites were down). Includes any job system found and matching job titles.
- `boards.json`: design roles from job boards and company job systems on the same date.

Limits:
- Of the 797 flagged companies, 582 have no website and could not be checked. Of the other 215, at most 24 showed a matching job, and some of those are false matches.
- 7,354 companies have no website and were not checked.
- LinkedIn and StartupJobs listings were not scanned.
- Career-page matches in `db_scan.jsonl` (`via: careers_page`) are simple text matches and include noise, such as service pages.

Scripts are in `pipeline/recheck/`.
