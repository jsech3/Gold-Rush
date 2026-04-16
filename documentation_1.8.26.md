# Documentation — 1.8.26 (TPM Job Hunter)

## Goal
Build a lightweight job-finding tool that surfaces **hidden opportunities** from Hacker News “Who is hiring?” threads and outputs a clean CSV filtered to roles that are a strong fit for Jack’s background.

Jack’s target constraints for this iteration:
- Location: **San Francisco or Remote**
- Compensation: **prefer $100k+** (but *do not drop good leads* when salary is missing)
- Role types: **Product roles**, **Business/Data Analyst roles**, and **Data/Analytics Engineering roles**
- Industry bias: **tech** / data / platform / cloud

## What We Started With
A single Python script (`tpm_job_hunter.py`) that:
- Generated a PRD markdown file.
- Queried the Algolia HN API broadly for “hiring”.
- Applied strict keyword filters.
- Wrote results to a CSV.

This version ran, but returned few/no matches and was noisy due to a broad query.

## Key Improvements Implemented

### 1) More Reliable Networking
We hardened the API request behavior:
- Use **HTTPS** for Algolia endpoints.
- Add **timeouts**.
- Add **HTTP status error handling** and **JSON parsing safeguards** so the script fails gracefully rather than crashing.

### 2) Use the Correct Data Source: “Ask HN: Who is hiring?”
We changed the scraping strategy to:
- Search Algolia for recent **“Ask HN: Who is hiring”** stories.
- For each story, fetch the full comment tree using Algolia’s **items API** (`/api/v1/items/<story_id>`).
- Flatten thread comments into a list of “post-like” records.

This dramatically increased the number of job postings available for filtering.

### 3) Text Normalization (HTML Cleanup)
HN posts are HTML-encoded. We added a normalization step:
- **HTML unescape** (e.g., `&amp;` → `&`).
- Strip HTML tags.
- Collapse whitespace.

This improved keyword matching, salary parsing, and made snippets readable.

### 4) Salary Extraction + “Practical” Filtering
HN posts often omit salary. We implemented a heuristic salary parser and a practical policy:

**Extraction**
- Parse values like:
  - `$130k-$275k`
  - `$178,500`
  - `115k - 180k`

**Practical policy (current default)**
- If salary is listed: **require min salary >= $100k**.
- If salary is missing: **keep the row**, but mark it as unknown.

The CSV now includes:
- `Salary Listed`
- `Meets $100k+`
- `Min Salary USD`
- `Max Salary USD`

> Note: Salary parsing is heuristic. Currency detection is not strict; some non-USD salaries may be interpreted numerically.

### 5) Role Classification for “Good Fit” Roles
We used Jack’s resume to define best-fit lanes and updated classification logic to prefer:
- **Product** (PM/TPM/product manager/product lead/etc.)
- **Business / Data Analyst** (data analyst, BI, analytics, product analyst, etc.)
- **Data / Analytics Engineering** (data engineer, analytics engineer, pipelines, dbt, airflow, etc.)

We also added a **generic SWE exclusion** so broad “software engineer/backend/full-stack/devops” postings don’t dominate the results unless the post explicitly matches the target tracks.

### 6) Location Filtering
We enforce SF/Remote matching using keyword heuristics:
- Remote indicators: `remote`, `work from home`, `wfh`, `anywhere`
- SF indicators: `san francisco`, `sf`, `bay area`

## Output
The script writes:
- `README_PRD.md` (generated PRD-style documentation)
- `TPM_Jobs_YYYY-MM-DD.csv` (the job results)

The CSV fields include:
- `Date`
- `Source`
- `Role Match`
- `Salary Listed`
- `Meets $100k+`
- `Min Salary USD`
- `Max Salary USD`
- `Snippet`
- `Link`

## How To Run
From the project folder:
```bash
python3 tpm_job_hunter.py
```

Dependencies:
- `requests`
- `pandas`

## How To Tune It (Quick Knobs)
In `__main__` you can adjust:
- `days_back` (how far back to search)
- `min_salary_usd` (e.g., 100000)
- `require_salary` (strict salary-only mode)
- `include_unknown_salary` (keep rows without salary)
- `require_location` (SF/Remote gate)
- `require_tech` (tech keyword gate)

## Recommended Next Enhancements
- Add **currency detection** (USD-only unless explicitly specified).
- Add **title extraction** (try to pull role title/company from the post more reliably).
- Add a **company** column (heuristic parsing of `Company | Role | Location | Comp` formatted posts).
- Deduplicate near-identical posts.
- Add a mode for **BI-first** vs **DE-first** vs **Product-first** searching.

## Summary of Today’s Outcome
We turned a simple keyword scraper into a more robust pipeline that:
- Pulls directly from the correct HN hiring threads.
- Cleans text for better matching.
- Filters for SF/Remote + tech.
- Applies a realistic salary rule (don’t discard unknown salary).
- Classifies and prioritizes roles aligned with Jack’s current experience and career goals.


Proposed command (can be run from any folder):
cat <<'EOF' >> "$HOME/2026Projects/Job Searching/documentation_1.8.26.md"
## Scheduling and Automation (macOS)

Run the scraper automatically every day using a user-level launchd job. These commands use absolute paths and can be run from any folder.

### One-time setup
1) Copy the launchd plist into your LaunchAgents folder:
```bash
cp "$HOME/2026Projects/Job Searching/com.yourname.tpm_job_hunter.plist" ~/Library/LaunchAgents/
```

2) Make the run script executable:
```bash
chmod +x "$HOME/2026Projects/Job Searching/run_daily_job_hunter.sh"
```

3) Load the job (also runs once immediately because RunAtLoad=true):
```bash
launchctl unload ~/Library/LaunchAgents/com.yourname.tpm_job_hunter.plist 2>/dev/null || true
launchctl load  ~/Library/LaunchAgents/com.yourname.tpm_job_hunter.plist
```

4) Verify it’s loaded:
```bash
launchctl list | grep tpm_job_hunter || true
```

### Run on demand (optional)
```bash
launchctl start com.yourname.tpm_job_hunter
```

### Output locations
- CSV files: `$HOME/2026Projects/Job Searching/outputs`
- Logs: `$HOME/2026Projects/Job Searching/logs`
  - `launchd.out.log` — stdout
  - `launchd.err.log` — stderr

### Change the run time
1) Edit the plist:
```bash
open -a TextEdit ~/Library/LaunchAgents/com.yourname.tpm_job_hunter.plist
```
Update the `StartCalendarInterval` Hour/Minute values.

2) Reload to apply changes:
```bash
launchctl unload ~/Library/LaunchAgents/com.yourname.tpm_job_hunter.plist
launchctl load  ~/Library/LaunchAgents/com.yourname.tpm_job_hunter.plist
```

### Notes
- System impact is minimal: it runs briefly at the scheduled time, otherwise idle.
- The Mac must be awake at the scheduled time; adjust the time accordingly or configure wake scheduling if needed.
- Remove the job anytime:
```bash
launchctl unload ~/Library/LaunchAgents/com.yourname.tpm_job_hunter.plist
rm ~/Library/LaunchAgents/com.yourname.tpm_job_hunter.plist
```
EOF

Would you like me to run that append command for you now? If yes, I’ll execute it and then show the updated tail of the file to confirm. Summary: Ready to append the scheduling section; awaiting your go-ahead.