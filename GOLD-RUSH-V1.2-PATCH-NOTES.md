# Gold Rush v1.2 — Patch Notes

**Date:** February 25, 2026
**Author:** Your Name
**Applies to:** `$HOME/GoldRush/gold_rush.py`

---

## Issues Reported (Feb 25, 2026)

### Issue 1: Fake "Posted 12 hours ago" on all LinkedIn jobs
**Observed:** Hightouch Analytics Engineer and Talently Senior Analytics Engineer both displayed "Posted 12 hours ago" in the digest email, but checking LinkedIn directly showed 1 day ago and 2 days ago respectively.

**Root cause:** `parse_email_body()` hardcoded `posted_date = datetime.now() - timedelta(hours=12)` for every LinkedIn-parsed job (line 549). The actual relative time text from LinkedIn emails ("2 days ago", "Actively recruiting") was being ignored.

**Fix:** Added `_parse_relative_time()` helper that extracts actual posting age from LinkedIn email text fragments:
- Matches "X hours ago", "X days ago", "X weeks ago"
- "Actively recruiting" / "Just posted" → treated as 6 hours old
- Falls back to 24h (conservative) if no time info found

**Files changed:** `gold_rush.py` lines 433–462 (new function), line 504 (call site)

---

### Issue 2: Duplicate Waymo listings
**Observed:** Two separate "Business Intelligence Analyst" entries for Waymo appeared in the same digest (scores 69 and 67), both already closed by the time of viewing. They had different LinkedIn job IDs (view/4375754846 vs view/4375756826).

**Root cause:** Deduplication only hashed `title + company + link`. Same job posted with different LinkedIn IDs was treated as two unique jobs. No mechanism to detect closed listings.

**Fix:** Two-level deduplication in `process_and_store_jobs()`:
1. **Level 1 (existing):** Hash of title + company + cleaned URL (now strips utm_/tracking params before hashing)
2. **Level 2 (new):** Normalized title+company key (`generate_title_company_key()`) checked against last 7 days of DB entries AND current batch. Same job title at same company from different sources/URLs → deduplicated.

**Files changed:** `gold_rush.py` lines 157–192 (new utility functions), lines 658–724 (rewritten `process_and_store_jobs`)

---

### Issue 3: Amazon Tableau job linked to trabajo.org (scam site)
**Observed:** "Data-Driven Business Analyst | Tableau" at Amazon had an apply link pointing to `us.trabajo.org`, a known job scraping/scam aggregator. Not a real Amazon listing.

**Root cause:** JSearch API's `job_apply_link` field returns whatever URL it scraped — often third-party aggregator sites rather than the actual employer page. In the database, **12 out of 96 jobs** linked to bebee.com alone, all from JSearch API.

**Fix:** Added `BLOCKED_LINK_DOMAINS` list and `is_blocked_domain()` check in `search_jsearch_api()`. When a blocked domain is detected, the link is replaced with a LinkedIn job search URL via `build_linkedin_search_url()`.

**Blocked domains:**
- trabajo.org, bebee.com, jooble.org, talent.com
- neuvoo.com, careerjet.com, adzuna.com
- recruit.net, jobrapido.com, snagajob.com

**Files changed:** `gold_rush.py` lines 87–91 (domain list), lines 170–180 (utility functions), lines 602–608 (JSearch redirect logic)

---

### Issue 4: BeBee links throughout results
**Observed:** Multiple silver-tier jobs (Adobe Senior Delivery Ops Analyst, Windfall Senior Product Ops Analyst, etc.) linked to `us.bebee.com` — a low-quality aggregator that reposts jobs with tracking spam. Same root cause as Issue 3.

**Fix:** bebee.com included in `BLOCKED_LINK_DOMAINS`. All affected jobs now redirect to LinkedIn search instead.

---

### Bug Found During Investigation: JSearch API crash on null city/state
**Observed in logs:** Recurring error `unsupported operand type(s) for +: 'NoneType' and 'str'` on 2 of 3 JSearch API calls every run since Feb 18+. The "Remote" location search consistently failed.

**Root cause:** Line 703 did `job_data.get("job_city", "") + ", " + job_data.get("job_state", "")`. The JSearch API returns `null` (not empty string) for city/state on remote jobs, and `.get("job_city", "")` only applies the default when the key is missing — not when the value is explicitly `null`/`None`.

**Fix:** Changed to `city = job_data.get("job_city") or ""` which handles both missing and null values.

**Files changed:** `gold_rush.py` lines 597–600

---

### Additional Finding: Live path mismatch
**Discovered:** The LaunchAgent scheduler runs from `$HOME/GoldRush/gold_rush.py`, but the README and previous sessions referenced `$HOME/Job Searching/`. The AI-Projects copy was stale (last modified Feb 18, missing all v1.1 changes). All fixes were applied to the live path.

**Fix:** Both copies are now synced. README updated with correct live path.

---

## Improvements for More Gold-Tier Jobs

### Problem
In the last 7 days: 17 gold, 0 platinum, 79 silver, 56 bronze. All 17 gold jobs came from LinkedIn email alerts. JSearch API produced only 1 gold job total.

### Changes Made

**Expanded known company list (70+ companies, was ~15):**
Added major tech, finance, and startup companies to `KNOWN_TECH_COMPANIES` list. These get 7 company-quality points (up from 3 for unknown companies). Includes: Google, Meta, Apple, Netflix, Coinbase, Robinhood, Roku, Waymo, Scale AI, Palantir, Cloudflare, etc.

**Added search titles:** "Product Analyst" and "Senior Data Analyst" added to `TARGET_TITLES` in config.env.

**Increased API calls:** `MAX_JSEARCH_CALLS_PER_DAY` bumped from 3 to 6 (the configured max). Now that the null crash is fixed, all 6 calls will actually succeed.

### Recommendation: More LinkedIn Email Alerts
LinkedIn is the gold mine — literally. Set up daily alerts for these additional titles in SF Bay Area:
- "Product Analyst"
- "Senior Data Analyst"
- "Senior Business Analyst"

---

## Files Modified

| File | Changes |
|------|---------|
| `$HOME/GoldRush/gold_rush.py` | Blocked domains, timestamp fix, dedup overhaul, null crash fix, expanded companies |
| `$HOME/GoldRush/config.env` | Added 2 search titles, bumped API calls to 6/day |
| `$HOME/GoldRush/GOLD-RUSH-README.md` | Full rewrite with v1.2 docs, correct paths, changelog |
| AI-Projects copy | Synced to match live version |

---

## Verification

- `python3.13 -c "import py_compile; py_compile.compile('gold_rush.py', doraise=True)"` → **Syntax OK**
- All new utility functions tested: `clean_url`, `is_blocked_domain`, `build_linkedin_search_url`, `generate_title_company_key`, `_parse_relative_time` → **All passing**
- Scheduler confirmed running: `launchctl list | grep gold_rush` → **active (pid 0)**
- Next automatic run: **8:00am Feb 26** (or run manually with `python3.13 gold_rush.py`)
