# Gold Rush

> **Status:** Archived. This project was built to automate a personal job search; archived after the author accepted an offer. Code is preserved as a reference implementation.

An end-to-end personal job-search pipeline: scrape, dedupe, score, and surface fresh listings through a password-gated dashboard.

## What it does

Runs twice a day on a local Mac via `launchd`, pulling fresh job postings from three sources:

1. **Gmail IMAP** — parses LinkedIn / Indeed job-alert emails
2. **JSearch API** (RapidAPI) — active search across aggregated boards
3. **Hacker News "Who's Hiring"** — scraped via a companion script

Each job is scored 0–100 against configurable preferences (title, location, salary, company), stored in SQLite, deduplicated across sources, and delivered via:

- A morning + evening digest email
- Immediate alerts for high-score ("platinum") jobs
- A web dashboard updated on every run

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌──────────────────┐
│ Gmail IMAP      │───▶│              │    │                  │
├─────────────────┤    │  gold_rush   │───▶│  SQLite (local)  │
│ JSearch API     │───▶│   .py        │    │                  │
├─────────────────┤    │  (scoring +  │    └────────┬─────────┘
│ HN Who's Hiring │───▶│  dedup)      │             │
└─────────────────┘    │              │             ▼
                       └──────┬───────┘    ┌──────────────────┐
                              │            │ jobs.json        │
                              ▼            │ meta.json        │
                       ┌──────────────┐    │ (exported)       │
                       │  Email       │    └────────┬─────────┘
                       │  digest      │             │
                       └──────────────┘             ▼
                                         ┌──────────────────────┐
                                         │  Vite + React        │
                                         │  dashboard (Vercel)  │
                                         └──────────────────────┘
```

## Repo layout

```
.
├── gold_rush.py                 Main pipeline: sources → score → store → export → email
├── tpm_job_hunter.py            HN "Who's Hiring" scraper (runs earlier in the day)
├── run_daily_job_hunter.sh      Wrapper invoked by launchd
├── com.yourname.*.plist         launchd job definitions (twice-daily schedule)
├── config.env.template          Copy to config.env; fill in credentials + preferences
├── dashboard/                   Vite + React + TypeScript dashboard
└── docs (GOLD-RUSH-*.html/md)   Setup guides, patch notes, PRD
```

## Setup

1. `cp config.env.template config.env` and fill in:
   - Gmail address + [App Password](https://myaccount.google.com/apppasswords)
   - RapidAPI key for [JSearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)
   - Target titles, locations, salary floor, preferred companies
2. `pip install -r requirements.txt` *(or install deps listed at top of `gold_rush.py`)*
3. First run: `python gold_rush.py`
4. Schedule via launchd: update the `.plist` files with your paths and `launchctl load` them
5. Dashboard: `cd dashboard && npm install && npm run dev`

Full walkthrough in [`GOLD-RUSH-SETUP-GUIDE.html`](./GOLD-RUSH-SETUP-GUIDE.html).

## Dashboard

The companion dashboard is a static Vite + React app that reads `jobs.json` / `meta.json` from `public/`. It's password-gated via a Vite-baked env var (`VITE_DASHBOARD_PASSWORD`) — note this is client-side obfuscation, not real auth; fine for single-user personal use, not for anything sensitive.

The pipeline writes fresh JSON to the dashboard repo on each run and `git push`es; Vercel handles the deploy.

## License

MIT
