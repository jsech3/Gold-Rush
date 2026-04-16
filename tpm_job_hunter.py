import requests
import pandas as pd
from datetime import datetime, timedelta
import re
import html
import os

# ==========================================
# PART 1: The Product Manager (PRD Generator)
# ==========================================
def generate_prd():
    """Generates the formal PRD file for your portfolio."""
    prd_content = """# Product Requirements Document: TPM Job Scraper
**Author:** Your Name
**Status:** V1.0 (Live)
**Type:** Automation / Internal Tool

## 1. Problem Statement
Manual searching for niche "Technical Product Manager" (TPM) roles is inefficient. Standard boards are cluttered with non-technical or non-data roles, wasting hours of filtering time.

## 2. Goal & Success Metrics
**Goal:** Automate the aggregation of high-signal TPM Data jobs.
**Success Metrics:**
*   **Precision:** >80% of output jobs match "Data/AI TPM" criteria.
*   **Efficiency:** Execution time < 1 minute.
*   **Outcome:** Generate a clean CSV for rapid application.

## 3. Functional Requirements (Must-Haves)
*   **FR-01 (Source):** Scrape listings from high-signal startup sources (Hacker News / YC).
*   **FR-02 (Keywords):** Filter for "Product Manager" + ("Data" OR "AI" OR "SQL").
*   **FR-03 (Location):** Filter for "Remote" or "San Francisco".
*   **FR-04 (Exclusion):** Exclude "Director" or "10+ years" to target mid-level fit.
*   **FR-05 (Export):** Output to CSV for tracking.
"""
    with open("README_PRD.md", "w") as f:
        f.write(prd_content)
    print("✅ PRD Generated: README_PRD.md")

# ==========================================
# PART 2: The Engineer (The Scraper)
# ==========================================
def fetch_jobs(days_back=7):
    """Fetches 'Who is Hiring' posts from Hacker News (Algolia API)."""
    # Calculate timestamp for 7 days ago
    date_cutoff = int((datetime.now() - timedelta(days=days_back)).timestamp())

    url = f"https://hn.algolia.com/api/v1/search_by_date?query=Ask%20HN%3A%20Who%20is%20hiring&tags=story&numericFilters=created_at_i>{date_cutoff}&hitsPerPage=20"

    print(f"🔄 Scraping jobs from the last {days_back} days...")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"⚠️ Network/API error while fetching jobs: {e}")
        return []
    except ValueError as e:
        print(f"⚠️ Failed to parse API response as JSON: {e}")
        return []

    stories = data.get('hits', [])
    story_ids = [s.get('objectID') for s in stories if s.get('objectID')]
    if not story_ids:
        return []

    all_comments = []
    for story_id in story_ids:
        try:
            item_resp = requests.get(f"https://hn.algolia.com/api/v1/items/{story_id}", timeout=20)
            item_resp.raise_for_status()
            item_data = item_resp.json()
        except requests.RequestException:
            continue
        except ValueError:
            continue

        stack = list(item_data.get('children', []) or [])
        while stack:
            node = stack.pop()
            if not isinstance(node, dict):
                continue
            stack.extend(node.get('children', []) or [])

            text = node.get('text')
            if not text:
                continue

            all_comments.append(
                {
                    'comment_text': text,
                    'created_at': node.get('created_at'),
                    'objectID': node.get('id'),
                }
            )

    return all_comments

def normalize_text(raw_text):
    unescaped = html.unescape(raw_text or "")
    no_tags = re.sub(r"<[^<]+?>", " ", unescaped)
    collapsed = re.sub(r"\s+", " ", no_tags).strip()
    return collapsed

def extract_salary_bounds(text):
    """Extract min/max USD salary if present, else (None, None)."""
    if not text:
        return None, None

    t = text.lower()
    if "equity" in t and "$" not in t and "k" not in t:
        return None, None

    amounts = []
    for m in re.finditer(r"\$\s*([0-9]{2,3}(?:,[0-9]{3})+|[0-9]{2,3})(?:\s*(k))?", t):
        raw_num = m.group(1).replace(",", "")
        try:
            val = int(raw_num)
        except ValueError:
            continue
        if m.group(2) == "k":
            val *= 1000
        if 15000 <= val <= 2000000:
            amounts.append(val)

    for m in re.finditer(r"\b([0-9]{2,3})\s*k\b", t):
        try:
            val = int(m.group(1)) * 1000
        except ValueError:
            continue
        if 15000 <= val <= 2000000:
            amounts.append(val)

    if not amounts:
        return None, None

    return min(amounts), max(amounts)

def classify_role(text):
    t = (text or "").lower()

    swe_exclude = [
        "software engineer",
        "swe",
        "backend engineer",
        "front end engineer",
        "frontend engineer",
        "full stack",
        "full-stack",
        "devops",
        "site reliability",
        "sre",
        "platform engineer",
        "mobile engineer",
        "ios engineer",
        "android engineer",
    ]

    product = [
        "product manager",
        "product management",
        "product owner",
        "product lead",
        "technical product",
        "tpm",
    ]
    analyst = [
        "data analyst",
        "business analyst",
        "analytics",
        "bi analyst",
        "business intelligence",
        "product analyst",
        "marketing analyst",
        "operations analyst",
    ]
    data_eng = [
        "data engineer",
        "analytics engineer",
        "data engineering",
        "data pipeline",
        "data pipelines",
        "airflow",
        "dagster",
        "dbt",
        "elt",
        "etl",
        "data warehousing",
        "data warehouse",
    ]

    # If it looks like a generic SWE post and doesn't explicitly mention the target tracks,
    # classify as Other so it gets filtered out.
    if any(k in t for k in swe_exclude):
        if not any(k in t for k in product) and not any(k in t for k in analyst) and not any(k in t for k in data_eng) and re.search(r"\b(pm|tpm)\b", t) is None:
            return "Other"

    if any(k in t for k in data_eng):
        return "Data / Analytics Engineering"
    if any(k in t for k in analyst):
        return "Business / Data Analyst"
    if any(k in t for k in product) or re.search(r"\b(pm|tpm)\b", t):
        return "Product"
    return "Other"

def filter_jobs(
    hits,
    require_tech=True,
    require_location=True,
    exclude_seniority=False,
    min_salary_usd=100000,
    require_salary=False,
    include_unknown_salary=True,
):
    """Applies TPM specific filters defined in the PRD."""
    valid_jobs = []
    
    for hit in hits:
        raw_text = hit.get('comment_text') or hit.get('story_text') or ""
        raw_title = hit.get('title') or ""
        cleaned_text = normalize_text(raw_text)
        cleaned_title = normalize_text(raw_title)
        full_text = f"{cleaned_title} {cleaned_text}".lower()

        role_category = classify_role(full_text)
        if role_category == "Other":
            continue

        tech_keywords = [
            "saas",
            "software",
            "platform",
            "api",
            "cloud",
            "data",
            "analytics",
            "ai",
            "ml",
            "machine learning",
            "sql",
            "python",
            "snowflake",
            "bigquery",
            "databricks",
            "aws",
            "gcp",
            "azure",
        ]
        if require_tech and not any(k in full_text for k in tech_keywords):
            continue

        # 3. Location Gating (SF or Remote) - FR-03
        loc_keywords = [
            "remote",
            "work from home",
            "wfh",
            "anywhere",
            "san francisco",
            "sf",
            "bay area",
        ]
        if require_location and not any(k in full_text for k in loc_keywords):
            continue

        # 4. Seniority Exclusion - FR-04
        exclude_terms = ["director", "vp", "head of", "10+ years", "principal"]
        if exclude_seniority and any(term in full_text for term in exclude_terms):
            continue

        min_sal, max_sal = extract_salary_bounds(full_text)
        salary_listed = min_sal is not None
        meets_salary = (min_sal is None) or (min_sal >= min_salary_usd)

        if require_salary and not salary_listed:
            continue
        if not salary_listed and not include_unknown_salary:
            continue
        if salary_listed and min_sal < min_salary_usd:
            continue

        snippet = cleaned_text[:300] + "..."

        job = {
            "Date": (hit.get('created_at') or "")[:10],
            "Source": "Hacker News",
            "Role Match": role_category,
            "Salary Listed": salary_listed,
            "Meets $100k+": meets_salary,
            "Min Salary USD": min_sal,
            "Max Salary USD": max_sal,
            "Snippet": snippet,
            "Link": f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        }
        valid_jobs.append(job)
        
    return valid_jobs

# ==========================================
# PART 3: Execution
# ==========================================
if __name__ == "__main__":
    # 1. Create the Documentation
    generate_prd()
    
    # 2. Run the Scraper
    days_back = 30
    raw_hits = fetch_jobs(days_back=days_back)
    tpm_jobs = filter_jobs(
        raw_hits,
        require_tech=True,
        require_location=True,
        exclude_seniority=False,
        min_salary_usd=100000,
        require_salary=False,
        include_unknown_salary=True,
    )
    
    # 3. Export Data - FR-05
    if tpm_jobs:
        df = pd.DataFrame(tpm_jobs)
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)
        filename = f"TPM_Jobs_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.csv"
        output_path = os.path.join(output_dir, filename)
        df.to_csv(output_path, index=False)
        print(f"✅ Success! Found {len(tpm_jobs)} relevant jobs.")
        print(f"📂 Saved to: {output_path}")
    else:
        print(f"⚠️ No matching jobs found in the last {days_back} days. Try increasing the date range.")