# Gold Rush — Automated Job Finder

**Version:** 1.2
**Last Updated:** February 24, 2026
**Owner:** Your Name
**Live directory:** `$HOME/GoldRush/`

---

## What It Does

Gold Rush runs twice a day and emails you a scored digest of fresh BA/analyst jobs before most people apply. It pulls from three sources, deduplicates everything, scores each job 0–100, and sends one clean email.

---

## Daily Schedule

| Time | What runs | What it produces |
|------|-----------|-----------------|
| 7:00am | tpm_job_hunter.py | Today's HN jobs → CSV in outputs/ |
| 8:00am | gold_rush.py | Reads all 3 sources → scores → emails digest to your-email@example.com |
| 7:00pm | gold_rush.py | Evening run — catches jobs posted during the day |

---

## Three Job Sources

### 1. LinkedIn / Indeed Email Alerts (email parsing)
- Gold Rush logs into Gmail via IMAP and reads job alert emails that arrived in the last 24 hours
- Parses job titles, companies, salary, and links from the HTML body of each alert email
- **Post dates are extracted from email text** (e.g., "2 days ago", "Actively recruiting") — no longer hardcoded
- **Alerts set up on:** BI Developer, Operations Analyst, Analytics Engineer, BI Analyst, Data Analyst, Business Data Analyst (all → San Francisco Bay Area, daily frequency)
- Requires: `EMAIL_ADDRESS` and `EMAIL_APP_PASSWORD` in config.env
- **This is the primary source of gold-tier jobs** — produces ~90% of high-scoring results

### 2. JSearch API
- Makes up to 6 API calls per day to jsearch.p.rapidapi.com (RapidAPI)
- Searches your `TARGET_TITLES` × `TARGET_LOCATIONS` from config.env
- Currently searching: 9 titles × 3 locations (capped at 6 calls/day)
- **Free tier:** 200 requests/month (6/day × 2 runs = ~360/month — monitor usage)
- **Blocked domains:** Links to scam/aggregator sites (trabajo.org, bebee.com, etc.) are automatically redirected to a LinkedIn job search URL instead
- Requires: `JSEARCH_API_KEY` in config.env

### 3. Hacker News (via tpm_job_hunter CSV)
- tpm_job_hunter.py scrapes the monthly HN "Who's Hiring" thread at 7:00am daily
- Gold Rush reads the CSV it produces, filters to relevant roles, and parses company/title
- **Filters applied:**
  - Role must be: `Business / Data Analyst` or `Data / Analytics Engineering`
  - Skips non-US postings (Germany, UK, EU, Canada, etc.)
  - Skips "seeking work" posts
  - Skips engineer/designer/sales/DevRel/intern titles
  - Skips entries where company/title can't be cleanly parsed

---

## Scoring System (0–100)

Each job is scored on six factors:

| Factor | Max Points | Logic |
|--------|-----------|-------|
| **Title match** | 35 | Exact match against target titles (Business Data Analyst = 35, Analytics Engineer = 31, Data Analyst = 30, etc.) Partial matches get 18–24 |
| **Salary** | 25 | $180k+ = 25pts, $150k+ = 22pts, $120k+ = 18pts, $100k+ = 14pts, $80k+ = 8pts, unknown = 5pts |
| **Freshness** | 15 | <6hrs = 15pts, <12hrs = 12pts, <24hrs = 9pts, <48hrs = 5pts |
| **Company quality** | 10 | Preferred companies (config.env) = 10pts, known tech (70+ companies) = 7pts, unknown = 3pts |
| **Location match** | 10 | Remote/SF/Bay Area = 10pts, greater Bay = 8pts, elsewhere in CA = 6pts, other = 3pts |
| **Seniority fit** | 5 | Senior/Lead = 5pts, Staff/Director = 3pts, Mid-level (default) = 4pts, Junior/Intern = 1pt |

**Floor:** 30 (a title match alone guarantees visibility)

### Tiers

| Tier | Score | Email treatment |
|------|-------|----------------|
| Platinum | 90–100 | Top of digest + immediate alert |
| Gold | 75–89 | Featured in digest |
| Silver | 60–74 | Listed in digest |
| Bronze | <60 | Stored in DB, not emailed |

---

## Blocked Domains (v1.2)

JSearch API sometimes returns apply links that point to scam job aggregators instead of the actual employer. These domains are blocked — when detected, the link is replaced with a LinkedIn job search URL:

- trabajo.org, bebee.com, jooble.org, talent.com
- neuvoo.com, careerjet.com, adzuna.com
- recruit.net, jobrapido.com, snagajob.com

To add more: edit `BLOCKED_LINK_DOMAINS` list in gold_rush.py.

---

## Deduplication (v1.2)

Two-level dedup prevents the same job from showing up multiple times:

1. **Link-based:** Hash of title + company + cleaned URL (tracking params stripped). Catches exact reposts.
2. **Title+Company:** Normalized text comparison across last 7 days. Catches the same job posted on LinkedIn AND JSearch with different URLs (e.g., the duplicate Waymo listings).

---

## Email Digest

Sent to: `your-email@example.com`
Triggered when: any platinum, gold, or silver jobs found
Contains: platinum → gold → silver jobs with title, company, location, salary, score, source, and Apply link

---

## Database

**Location:** `gold_rush.db` (SQLite)
**Table:** `jobs`

| Column | Description |
|--------|-------------|
| `title` | Job title |
| `company` | Company name |
| `location` | Location string |
| `salary_min` / `salary_max` | Parsed salary range |
| `source` | `jsearch_api`, `linkedin_email`, `indeed_email`, or `hacker_news` |
| `posted_date` | When the job was posted (parsed from source, not hardcoded) |
| `found_date` | When Gold Rush stored it |
| `goldness_score` | 0–100 score |
| `tier` | platinum / gold / silver / bronze |
| `emailed` | Whether it was included in a digest |
| `applied` | Manual flag (set this yourself when you apply) |
| `created_at` | DB insert timestamp |

**Useful queries:**
```sql
-- All jobs found today
SELECT title, company, source, tier, goldness_score
FROM jobs WHERE DATE(found_date) = DATE('now')
ORDER BY goldness_score DESC;

-- Silver+ jobs not yet applied to
SELECT title, company, link, goldness_score
FROM jobs WHERE tier IN ('platinum','gold','silver') AND applied = 0
ORDER BY found_date DESC;

-- Jobs by source breakdown
SELECT source, COUNT(*), AVG(goldness_score)
FROM jobs GROUP BY source;

-- Gold jobs from last 7 days
SELECT title, company, goldness_score, salary_min, salary_max, location
FROM jobs WHERE tier IN ('platinum','gold') AND found_date > datetime('now', '-7 days')
ORDER BY goldness_score DESC;
```

---

## Configuration

**File:** `config.env` in GoldRush folder

| Variable | Current value | Description |
|----------|--------------|-------------|
| `EMAIL_ADDRESS` | your-email@example.com | Gmail address |
| `EMAIL_APP_PASSWORD` | set | Gmail App Password (not your real password) |
| `JSEARCH_API_KEY` | set | RapidAPI key for JSearch |
| `TARGET_TITLES` | Business Data Analyst, Business Analyst, Data Analyst, BI Analyst, BI Developer, Operations Analyst, Analytics Engineer, Product Analyst, Senior Data Analyst | Titles for API searches |
| `TARGET_LOCATIONS` | San Francisco, Remote, Bay Area | Locations for API searches |
| `MIN_SALARY` | 90000 | Floor for salary scoring |
| `PREFERRED_SALARY` | 110000 | Target salary |
| `MAX_JSEARCH_CALLS_PER_DAY` | 6 | API call limit per run (200/month free tier — monitor) |
| `PREFERRED_COMPANIES` | Stripe, Figma, Notion, Databricks, Snowflake, Salesforce, Adobe, Workday, Airbnb, Lyft, Instacart, Anthropic, OpenAI | Companies that get +10 quality score |

---

## File Structure

```
$HOME/GoldRush/          ← LIVE (this is what the scheduler runs)
├── gold_rush.py                       # Main script (v1.2)
├── config.env                         # Your credentials and preferences
├── gold_rush.db                       # SQLite database (all jobs ever found)
├── logs/
│   ├── gold_rush.log                  # Main run log
│   ├── launchd.out.log                # Scheduler stdout
│   └── launchd.err.log                # Scheduler stderr
├── GOLD-RUSH-README.md                # This file
└── SETUP-GUIDE.md                     # Initial setup instructions

~/Library/LaunchAgents/
└── com.yourname.gold_rush.plist    # macOS scheduler (8am + 7pm daily)
```

**Note:** There is also a copy at `~/Desktop/Your Name/2025/Digital Projects/AI-Projects/Job Searching/` — that is NOT the live version. The scheduler runs from `$HOME/GoldRush/`.

---

## Tips for More Gold Jobs

1. **Add more LinkedIn email alerts** — These produce ~90% of gold-tier results. Set up alerts for "Product Analyst", "Senior Data Analyst", and "Senior Business Analyst" in SF Bay Area.
2. **Preferred companies list** — Adding a company to `PREFERRED_COMPANIES` in config.env gives it +10 instead of +7. Keep the list updated with companies you'd want to work at.
3. **Salary visibility** — Jobs with listed salary score much higher. LinkedIn "Easy Apply" jobs more often show salary.

---

## Changelog

### v1.2 (February 24, 2026)
- **Blocked domains:** trabajo.org, bebee.com, and 8 other scam/aggregator sites auto-redirect to LinkedIn search
- **Accurate timestamps:** LinkedIn email jobs now parse relative time ("2 days ago") instead of hardcoding "12 hours ago"
- **Better dedup:** Two-level deduplication catches same job from different sources (e.g., duplicate Waymo listings)
- **Fixed crash:** JSearch API no longer crashes when city/state is null (`NoneType + str` error)
- **Expanded companies:** 70+ known tech/finance companies in scoring list (was ~15)
- **More API searches:** Bumped JSearch to 6 calls/day, added Product Analyst and Senior Data Analyst titles
- **Correct live path:** Documented that `$HOME/GoldRush/` is the live directory

### v1.1 (February 17, 2026)
- Added salary parsing from LinkedIn emails
- Added location and seniority scoring
- Rebalanced scoring weights (6 factors instead of 4)

### v1.0 (February 6, 2026)
- Initial release: 3 sources, 4-factor scoring, email digest

---

## Maintenance

**If you stop receiving emails:**
```bash
tail -50 $HOME/GoldRush/logs/gold_rush.log
launchctl list | grep gold_rush
```

**To run manually:**
```bash
cd $HOME/GoldRush
/opt/homebrew/opt/python@3.13/bin/python3.13 gold_rush.py
```

**To stop the scheduler:**
```bash
launchctl unload ~/Library/LaunchAgents/com.yourname.gold_rush.plist
```

**To restart the scheduler:**
```bash
launchctl load ~/Library/LaunchAgents/com.yourname.gold_rush.plist
```
