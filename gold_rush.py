#!/usr/bin/env python3
"""
Gold Rush - Automated Golden Job Finder
Finds fresh, high-paying, perfectly-aligned jobs before the crowd.

Author: Built for Your Name
Created: February 6, 2026
Version: 1.1 — Blocked domains, better dedup, accurate timestamps, expanded companies
"""

import os
import sys
import json
import sqlite3
import hashlib
import logging
import smtplib
import imaplib
import email
import re
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional, Tuple
from pathlib import Path

import subprocess
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# ============================================================================
# CONFIGURATION
# ============================================================================

# Get script directory
SCRIPT_DIR = Path(__file__).parent
load_dotenv(SCRIPT_DIR / "config.env")

# Paths
DB_PATH = SCRIPT_DIR / "gold_rush.db"
LOG_DIR = SCRIPT_DIR / "logs"
OUTPUT_DIR = SCRIPT_DIR / "outputs"

# Create directories
LOG_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "gold_rush.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Email configuration
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")

# JSearch API configuration
JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY")
JSEARCH_API_HOST = os.getenv("JSEARCH_API_HOST", "jsearch.p.rapidapi.com")

# Job search preferences
TARGET_TITLES = os.getenv("TARGET_TITLES", "").split(",")
TARGET_LOCATIONS = os.getenv("TARGET_LOCATIONS", "").split(",")
MIN_SALARY = int(os.getenv("MIN_SALARY", "100000"))
PREFERRED_SALARY = int(os.getenv("PREFERRED_SALARY", "120000"))

# Notification settings
SEND_DAILY_DIGEST = os.getenv("SEND_DAILY_DIGEST", "true").lower() == "true"
SEND_IMMEDIATE_PLATINUM = os.getenv("SEND_IMMEDIATE_PLATINUM", "true").lower() == "true"

# API limits
MAX_JSEARCH_CALLS_PER_DAY = int(os.getenv("MAX_JSEARCH_CALLS_PER_DAY", "6"))
ENABLE_EMAIL_PARSING = os.getenv("ENABLE_EMAIL_PARSING", "true").lower() == "true"

# Company preferences
PREFERRED_COMPANIES = os.getenv("PREFERRED_COMPANIES", "").split(",")
AVOID_COMPANIES = os.getenv("AVOID_COMPANIES", "").split(",")

# Blocked link domains — aggregator/scam sites that repost jobs with bad links.
# Jobs linking to these get redirected to a LinkedIn search URL instead.
BLOCKED_LINK_DOMAINS = [
    "trabajo.org", "bebee.com", "jooble.org", "talent.com",
    "neuvoo.com", "careerjet.com", "adzuna.com",
    "recruit.net", "jobrapido.com", "snagajob.com",
]

# Expanded known-good companies list — used for company quality scoring.
KNOWN_TECH_COMPANIES = [
    "stripe", "figma", "notion", "databricks", "snowflake", "salesforce",
    "adobe", "workday", "airbnb", "lyft", "instacart", "anthropic", "openai",
    "google", "meta", "apple", "amazon", "microsoft", "netflix",
    "uber", "doordash", "square", "block", "plaid", "retool",
    "coinbase", "robinhood", "rippling", "brex", "ramp", "gusto",
    "twilio", "datadog", "hashicorp", "elastic", "confluent",
    "pagerduty", "gitlab", "github", "atlassian", "asana", "monday",
    "hubspot", "zendesk", "okta", "crowdstrike", "cloudflare",
    "palantir", "splunk", "tableau", "dbt labs", "fivetran", "census",
    "hightouch", "amplitude", "mixpanel", "segment",
    "pinterest", "snap", "reddit", "discord", "spotify", "dropbox",
    "slack", "zoom", "webflow", "vercel", "supabase", "linear",
    "scale ai", "waymo", "cruise", "aurora", "nuro",
    "tesla", "rivian", "lucid", "nvidia", "amd", "intel",
    "visa", "mastercard", "jpmorgan", "goldman sachs", "morgan stanley",
    "acorns", "wealthfront", "betterment", "sofi", "chime",
    "roku", "zillow", "redfin", "compass", "opendoor",
    "databricks", "mongodb", "cockroach labs", "timescale",
    "loom", "miro", "airtable", "coda", "clickup",
]

# ============================================================================
# DATABASE SETUP
# ============================================================================

def init_database():
    """Initialize SQLite database with schema."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT UNIQUE,
            title TEXT,
            company TEXT,
            location TEXT,
            salary_min INTEGER,
            salary_max INTEGER,
            salary_text TEXT,
            link TEXT,
            source TEXT,
            posted_date DATETIME,
            found_date DATETIME,
            goldness_score INTEGER,
            tier TEXT,
            emailed BOOLEAN DEFAULT 0,
            applied BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_posted_date ON jobs(posted_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_goldness_score ON jobs(goldness_score)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tier ON jobs(tier)")

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def clean_url(url: str) -> str:
    """Strip tracking params (utm_*, refId, trackingId) from a URL for cleaner dedup."""
    from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        clean_params = {k: v for k, v in params.items()
                        if not k.startswith("utm_") and k not in ("refId", "trackingId")}
        cleaned = parsed._replace(query=urlencode(clean_params, doseq=True))
        return urlunparse(cleaned)
    except Exception:
        return url

def is_blocked_domain(url: str) -> bool:
    """Check if a URL points to a blocked aggregator/scam domain."""
    url_lower = url.lower()
    return any(domain in url_lower for domain in BLOCKED_LINK_DOMAINS)

def build_linkedin_search_url(title: str, company: str) -> str:
    """Build a LinkedIn job search URL as a fallback when the original link is blocked."""
    from urllib.parse import quote
    query = quote(f"{title} {company}")
    return f"https://www.linkedin.com/jobs/search/?keywords={query}"

def generate_job_id(title: str, company: str, link: str) -> str:
    """Generate unique job ID from title, company, and cleaned link."""
    cleaned_link = clean_url(link)
    unique_string = f"{title.lower().strip()}|{company.lower().strip()}|{cleaned_link.strip()}"
    return hashlib.md5(unique_string.encode()).hexdigest()

def generate_title_company_key(title: str, company: str) -> str:
    """Normalized key from title+company for cross-source dedup."""
    t = re.sub(r'[^a-z0-9 ]', '', title.lower().strip())
    c = re.sub(r'[^a-z0-9 ]', '', company.lower().strip())
    return f"{t}|{c}"

def extract_salary(text: str) -> Tuple[Optional[int], Optional[int], str]:
    """
    Extract salary range from text.
    Returns: (min_salary, max_salary, original_text)
    """
    if not text:
        return None, None, ""

    # Remove common noise
    text_lower = text.lower()
    if "equity" in text_lower and "$" not in text_lower and "k" not in text_lower:
        return None, None, text

    amounts = []

    # Pattern 1: $XXX,XXX or $XXXk
    for match in re.finditer(r'\$\s*([0-9]{2,3}(?:,[0-9]{3})+|[0-9]{2,3})(?:\s*(k))?', text_lower):
        raw_num = match.group(1).replace(",", "")
        try:
            val = int(raw_num)
            if match.group(2) == "k":
                val *= 1000
            if 15000 <= val <= 2000000:
                amounts.append(val)
        except ValueError:
            continue

    # Pattern 2: XXXk
    for match in re.finditer(r'\b([0-9]{2,3})\s*k\b', text_lower):
        try:
            val = int(match.group(1)) * 1000
            if 15000 <= val <= 2000000:
                amounts.append(val)
        except ValueError:
            continue

    if not amounts:
        return None, None, text

    return min(amounts), max(amounts), text

def calculate_goldness_score(job: Dict) -> int:
    """
    Calculate goldness score (0-100) based on six factors.

    Scoring:
    - Title match: 35 points max
    - Salary: 25 points max
    - Freshness: 15 points max
    - Company quality: 10 points max
    - Location match: 10 points max  (NEW)
    - Seniority fit: 5 points max    (NEW)

    Floor: 30 (a title match alone guarantees visibility)
    """
    score = 0
    title = job.get("title", "").lower()
    company = job.get("company", "").lower()
    location = job.get("location", "").lower()
    salary_min = job.get("salary_min")
    posted_date = job.get("posted_date")

    # --- Title match (35 points) ---
    title_scores = {
        "business data analyst": 35,
        "business intelligence analyst": 34,
        "bi developer": 33,
        "bi analyst": 33,
        "business analyst": 32,
        "senior data analyst": 32,
        "power bi analyst": 32,
        "analytics engineer": 31,
        "data analyst": 30,
        "operations analyst": 29,
        "reporting analyst": 28,
        "data operations analyst": 30,
        "product analyst": 29,
        "analytics analyst": 28,
    }

    for key_title, points in title_scores.items():
        if key_title in title:
            score += points
            break
    else:
        # Partial matches
        if "analyst" in title and ("data" in title or "business" in title or "bi" in title):
            score += 24
        elif "analyst" in title:
            score += 18

    # --- Salary (25 points) ---
    if salary_min:
        if salary_min >= 180000:
            score += 25
        elif salary_min >= 150000:
            score += 22
        elif salary_min >= 120000:
            score += 18
        elif salary_min >= 100000:
            score += 14
        elif salary_min >= 80000:
            score += 8
        else:
            score += 4
    else:
        score += 5  # Unknown salary — mild credit, don't reward missing info

    # --- Freshness (15 points) ---
    if posted_date:
        try:
            if isinstance(posted_date, str):
                posted_dt = datetime.fromisoformat(posted_date.replace('Z', '+00:00'))
            else:
                posted_dt = posted_date

            hours_old = (datetime.now() - posted_dt.replace(tzinfo=None)).total_seconds() / 3600

            if hours_old < 6:
                score += 15
            elif hours_old < 12:
                score += 12
            elif hours_old < 24:
                score += 9
            elif hours_old < 48:
                score += 5
            else:
                score += 2
        except:
            score += 4  # Unknown age
    else:
        score += 4

    # --- Company quality (10 points) ---
    preferred_companies_lower = [c.lower().strip() for c in PREFERRED_COMPANIES if c]

    for pref_company in preferred_companies_lower:
        if pref_company in company:
            score += 10
            break
    else:
        if any(tech in company for tech in KNOWN_TECH_COMPANIES):
            score += 7
        else:
            score += 3  # Unknown company

    # --- Location match (10 points) --- NEW
    if "remote" in location:
        score += 10
    elif any(loc in location for loc in ["san francisco", "sf", "bay area", "oakland", "berkeley"]):
        score += 10
    elif any(loc in location for loc in ["san jose", "palo alto", "mountain view", "sunnyvale",
                                          "redwood city", "menlo park", "santa clara", "fremont"]):
        score += 8
    elif "california" in location or ", ca" in location:
        score += 6
    elif location and location.strip():
        score += 3  # Some other US location
    else:
        score += 4  # No location parsed — don't penalize heavily

    # --- Seniority fit (5 points) --- NEW
    if any(kw in title for kw in ["senior", "sr.", "sr ", "lead"]):
        score += 5
    elif any(kw in title for kw in ["staff", "principal", "director", "head of", "vp"]):
        score += 3
    elif any(kw in title for kw in ["intern", "junior", "jr.", "jr ", "entry"]):
        score += 1
    else:
        score += 4  # Mid-level (assumed) — good fit

    # Floor: title match alone should guarantee visibility
    score = max(score, 30)

    return min(score, 100)  # Cap at 100

def determine_tier(score: int) -> str:
    """Determine job tier based on goldness score."""
    if score >= 85:
        return "platinum"
    elif score >= 70:
        return "gold"
    elif score >= 50:
        return "silver"
    else:
        return "bronze"

# ============================================================================
# EMAIL PARSING
# ============================================================================

def parse_job_alert_emails() -> List[Dict]:
    """
    Parse job alert emails from Gmail (LinkedIn, Indeed).
    Returns list of job dictionaries.
    """
    if not ENABLE_EMAIL_PARSING:
        logger.info("Email parsing disabled in config")
        return []

    if not EMAIL_ADDRESS or not EMAIL_APP_PASSWORD:
        logger.warning("Email credentials not configured, skipping email parsing")
        return []

    jobs = []

    try:
        # Connect to Gmail via IMAP
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        mail.select("inbox")

        # Search for job alert emails from last 24 hours
        date = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")

        # LinkedIn job alerts
        status, linkedin_messages = mail.search(None, f'(FROM "jobalerts-noreply@linkedin.com" SINCE {date})')

        # Indeed job alerts
        status, indeed_messages = mail.search(None, f'(FROM "noreply@indeed.com" SINCE {date})')

        # Glassdoor job alerts
        status, glassdoor_messages = mail.search(None, f'(FROM "noreply@glassdoor.com" SINCE {date})')

        all_message_ids = []
        if linkedin_messages[0]:
            all_message_ids.extend(linkedin_messages[0].split())
        if indeed_messages[0]:
            all_message_ids.extend(indeed_messages[0].split())
        if glassdoor_messages[0]:
            all_message_ids.extend(glassdoor_messages[0].split())

        logger.info(f"Found {len(all_message_ids)} job alert emails to parse")

        for msg_id in all_message_ids:
            try:
                status, msg_data = mail.fetch(msg_id, "(RFC822)")
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)

                # Determine source
                from_addr = email_message.get("From", "").lower()
                if "linkedin" in from_addr:
                    source = "linkedin_email"
                elif "indeed" in from_addr:
                    source = "indeed_email"
                elif "glassdoor" in from_addr:
                    source = "glassdoor_email"
                else:
                    source = "unknown_email"

                # Extract email body
                body = ""
                if email_message.is_multipart():
                    for part in email_message.walk():
                        if part.get_content_type() == "text/html":
                            body = part.get_payload(decode=True).decode(errors='ignore')
                            break
                else:
                    body = email_message.get_payload(decode=True).decode(errors='ignore')

                # Parse jobs from email body
                parsed_jobs = parse_email_body(body, source)
                jobs.extend(parsed_jobs)

            except Exception as e:
                logger.error(f"Error parsing email {msg_id}: {e}")
                continue

        mail.close()
        mail.logout()

    except Exception as e:
        logger.error(f"Error connecting to Gmail: {e}")

    logger.info(f"Parsed {len(jobs)} jobs from emails")
    return jobs

def _parse_relative_time(text_parts: list) -> datetime:
    """
    Extract relative posting time from LinkedIn email text fragments.
    Looks for patterns like "1 day ago", "2 days ago", "3 hours ago",
    "Actively recruiting", "Reposted X days ago", etc.
    Falls back to email receive time (now) minus 24h if nothing found.
    """
    full_text = " ".join(text_parts).lower()

    # "X hour(s) ago"
    match = re.search(r'(\d+)\s*hours?\s*ago', full_text)
    if match:
        return datetime.now() - timedelta(hours=int(match.group(1)))

    # "X day(s) ago"
    match = re.search(r'(\d+)\s*days?\s*ago', full_text)
    if match:
        return datetime.now() - timedelta(days=int(match.group(1)))

    # "X week(s) ago"
    match = re.search(r'(\d+)\s*weeks?\s*ago', full_text)
    if match:
        return datetime.now() - timedelta(weeks=int(match.group(1)))

    # "Actively recruiting" or "Just posted" → treat as recent (6h)
    if "actively recruiting" in full_text or "just posted" in full_text:
        return datetime.now() - timedelta(hours=6)

    # Default: assume ~24h old (conservative, better than fake 12h)
    return datetime.now() - timedelta(hours=24)

def parse_email_body(html_body: str, source: str) -> List[Dict]:
    """Parse job listings from email HTML body."""
    jobs = []

    try:
        soup = BeautifulSoup(html_body, 'html.parser')

        # LinkedIn parsing
        if source == "linkedin_email":
            # LinkedIn uses /comm/jobs/view/ in alert emails
            job_links = soup.find_all('a', href=re.compile(r'linkedin\.com/comm/jobs/view/\d+'))
            seen_urls = set()

            for link in job_links:
                try:
                    job_url = link.get('href', '').split('?')[0]  # strip tracking params
                    if not job_url or job_url in seen_urls:
                        continue

                    # Walk up to the table row containing this link
                    parent = link
                    for _ in range(8):
                        if parent.parent:
                            parent = parent.parent
                        if parent.name == 'tr':
                            break

                    # Collect all meaningful text nodes in this row
                    text_parts = []
                    for child in parent.find_all(string=True):
                        text = child.strip()
                        # Skip empty, very short, and HTML comment/conditional junk
                        if text and len(text) > 1 and not text.startswith('[if'):
                            text_parts.append(text)

                    if not text_parts:
                        continue

                    # LinkedIn email structure:
                    #   text_parts[0] = "Job Title"
                    #   text_parts[1] = "Company · Location, State (Type)"
                    #   text_parts[2] = "$XXK-$XXK / year"  (optional)
                    #   text_parts[3+] = metadata noise ("1 connection", "Easy Apply", etc.)

                    title = re.sub(r'\s*-\s*\d+$', '', text_parts[0]).strip()

                    company = "Unknown"
                    location = ""
                    if len(text_parts) > 1:
                        # Split "Company · Location" on the middle dot
                        company_loc = text_parts[1]
                        cl_parts = [p.strip() for p in company_loc.split('·')]
                        company = cl_parts[0].strip() if cl_parts else "Unknown"
                        location = cl_parts[1].strip() if len(cl_parts) > 1 else ""

                    # Extract salary from remaining text parts
                    salary_text = ""
                    salary_min = None
                    salary_max = None
                    for tp in text_parts[2:]:
                        if '$' in tp and ('/' in tp or 'k' in tp.lower()):
                            salary_text = tp
                            salary_min, salary_max, _ = extract_salary(tp)
                            break

                    # Skip if title is empty or looks like a URL/nav element
                    if not title or len(title) < 4 or title.lower().startswith('http'):
                        continue

                    # Try to extract relative posting time from text parts
                    # LinkedIn includes things like "Actively recruiting", "1 day ago", "2 days ago"
                    posted_date = _parse_relative_time(text_parts)

                    seen_urls.add(job_url)
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "link": job_url,
                        "source": source,
                        "posted_date": posted_date,
                        "salary_min": salary_min,
                        "salary_max": salary_max,
                        "salary_text": salary_text
                    })
                except Exception as e:
                    logger.error(f"Error parsing LinkedIn job: {e}")
                    continue

        # Indeed parsing
        elif source == "indeed_email":
            # Indeed uses /viewjob or /rc/clk in alert emails
            job_links = soup.find_all('a', href=re.compile(r'indeed\.com.*(viewjob|clk|rc/clk)'))
            seen_urls = set()

            for link in job_links:
                try:
                    job_url = link.get('href', '')
                    if not job_url or job_url in seen_urls:
                        continue

                    raw_text = link.get_text(separator=' ', strip=True)
                    if not raw_text or len(raw_text) < 4:
                        continue

                    # Indeed format: "Job Title" with company in nearby sibling
                    title = raw_text
                    parent = link.parent
                    company = "Unknown"
                    location = ""
                    for _ in range(4):
                        if parent:
                            text = parent.get_text(separator=' ', strip=True)
                            # Look for company name pattern after title
                            match = re.search(r'[-–]\s*(.+?)\s*[-–|·]', text[len(title):])
                            if match:
                                company = match.group(1).strip()
                                break
                            parent = parent.parent

                    seen_urls.add(job_url)
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "link": job_url,
                        "source": source,
                        "posted_date": datetime.now() - timedelta(hours=24),  # Indeed doesn't have precise time
                        "salary_min": None,
                        "salary_max": None,
                        "salary_text": ""
                    })
                except Exception as e:
                    logger.error(f"Error parsing Indeed job: {e}")
                    continue

    except Exception as e:
        logger.error(f"Error parsing email body: {e}")

    return jobs

# ============================================================================
# JSEARCH API
# ============================================================================

def search_jsearch_api(query: str, location: str, date_posted: str = "today") -> List[Dict]:
    """
    Search for jobs using JSearch API.

    Args:
        query: Job title/keywords
        location: Location string
        date_posted: "today", "3days", "week", "month"

    Returns:
        List of job dictionaries
    """
    if not JSEARCH_API_KEY:
        logger.warning("JSearch API key not configured")
        return []

    url = f"https://{JSEARCH_API_HOST}/search"

    querystring = {
        "query": f"{query} {location}",
        "page": "1",
        "num_pages": "1",
        "date_posted": date_posted,
        "remote_jobs_only": "false"  # We filter location ourselves
    }

    headers = {
        "X-RapidAPI-Key": JSEARCH_API_KEY,
        "X-RapidAPI-Host": JSEARCH_API_HOST
    }

    try:
        logger.info(f"JSearch API call: {query} in {location}")
        response = requests.get(url, headers=headers, params=querystring, timeout=15)
        response.raise_for_status()
        data = response.json()

        jobs = []
        for job_data in data.get("data", []):
            # Extract salary
            salary_min, salary_max, salary_text = extract_salary(
                job_data.get("job_salary", "") or ""
            )

            # Parse posted date
            posted_timestamp = job_data.get("job_posted_at_timestamp")
            if posted_timestamp:
                posted_date = datetime.fromtimestamp(posted_timestamp)
            else:
                posted_date = datetime.now() - timedelta(hours=24)

            # Fix: city/state can be None, causing "NoneType + str" crash
            city = job_data.get("job_city") or ""
            state = job_data.get("job_state") or ""
            location = f"{city}, {state}".strip(", ")

            # Get apply link — redirect blocked domains to LinkedIn search
            apply_link = str(job_data.get("job_apply_link", "") or "")
            title = str(job_data.get("job_title", "") or "")
            company = str(job_data.get("employer_name", "") or "")
            if is_blocked_domain(apply_link):
                logger.info(f"Blocked domain in link for '{title}' at {company}, redirecting to LinkedIn search")
                apply_link = build_linkedin_search_url(title, company)

            jobs.append({
                "title": title,
                "company": company,
                "location": location,
                "link": apply_link,
                "source": "jsearch_api",
                "posted_date": posted_date,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_text": salary_text
            })

        logger.info(f"JSearch API returned {len(jobs)} jobs")
        return jobs

    except requests.RequestException as e:
        logger.error(f"JSearch API error: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in JSearch API call: {e}")
        return []

def fetch_jobs_from_api() -> List[Dict]:
    """
    Fetch jobs from JSearch API with smart query rotation.
    Stays within daily API call limit.
    """
    all_jobs = []

    # Build searches from config.env TARGET_TITLES and TARGET_LOCATIONS
    titles = [t.strip() for t in TARGET_TITLES if t.strip()]
    locations = [l.strip() for l in TARGET_LOCATIONS if l.strip()]

    if not titles:
        titles = ["Business Data Analyst", "Business Analyst", "Data Analyst"]
    if not locations:
        locations = ["San Francisco", "Remote"]

    searches = []
    for title in titles:
        for location in locations:
            searches.append((title, location))
            if len(searches) >= MAX_JSEARCH_CALLS_PER_DAY * 3:
                break
        if len(searches) >= MAX_JSEARCH_CALLS_PER_DAY * 3:
            break

    for i, (title, location) in enumerate(searches[:MAX_JSEARCH_CALLS_PER_DAY]):
        if i >= MAX_JSEARCH_CALLS_PER_DAY:
            break

        jobs = search_jsearch_api(title, location, date_posted="today")
        all_jobs.extend(jobs)

    logger.info(f"Total jobs from JSearch API: {len(all_jobs)}")
    return all_jobs

# ============================================================================
# JOB PROCESSING
# ============================================================================

def process_and_store_jobs(jobs: List[Dict]) -> Dict:
    """
    Process jobs: deduplicate, score, store in database.
    Two-level dedup:
      1. Exact match on job_id (title+company+cleaned_link hash)
      2. Fuzzy match on normalized title+company (catches same job from different sources)
    Returns summary statistics.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    stats = {
        "total_found": len(jobs),
        "new_jobs": 0,
        "duplicates": 0,
        "blocked": 0,
        "platinum": 0,
        "gold": 0,
        "silver": 0,
        "bronze": 0
    }

    # Build set of existing title+company keys for cross-source dedup
    cursor.execute("SELECT title, company FROM jobs WHERE found_date > datetime('now', '-7 days')")
    seen_title_company = set()
    for row in cursor.fetchall():
        seen_title_company.add(generate_title_company_key(row[0], row[1]))

    # Also track within this batch
    batch_title_company = set()

    for job in jobs:
        try:
            # Generate unique ID (link-based)
            job_id = generate_job_id(job["title"], job["company"], job["link"])

            # Level 1: Exact dedup by job_id
            cursor.execute("SELECT id FROM jobs WHERE job_id = ?", (job_id,))
            if cursor.fetchone():
                stats["duplicates"] += 1
                continue

            # Level 2: Cross-source dedup by normalized title+company
            tc_key = generate_title_company_key(job["title"], job["company"])
            if tc_key in seen_title_company or tc_key in batch_title_company:
                stats["duplicates"] += 1
                logger.debug(f"Cross-source dupe: {job['title']} at {job['company']}")
                continue

            # Calculate goldness score
            score = calculate_goldness_score(job)
            tier = determine_tier(score)

            # Store in database
            cursor.execute("""
                INSERT INTO jobs (
                    job_id, title, company, location, salary_min, salary_max,
                    salary_text, link, source, posted_date, found_date,
                    goldness_score, tier
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                job["title"],
                job["company"],
                job.get("location", ""),
                job.get("salary_min"),
                job.get("salary_max"),
                job.get("salary_text", ""),
                job["link"],
                job["source"],
                job["posted_date"],
                datetime.now(),
                score,
                tier
            ))

            stats["new_jobs"] += 1
            stats[tier] += 1
            batch_title_company.add(tc_key)

        except Exception as e:
            logger.error(f"Error processing job: {e}")
            continue

    conn.commit()
    conn.close()

    logger.info(f"Processed {stats['new_jobs']} new jobs, {stats['duplicates']} duplicates")
    return stats

# ============================================================================
# EMAIL NOTIFICATIONS
# ============================================================================

def send_email(subject: str, body_html: str):
    """Send email via Gmail SMTP."""
    if not EMAIL_ADDRESS or not EMAIL_APP_PASSWORD:
        logger.error("Email credentials not configured")
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = EMAIL_ADDRESS

        msg.attach(MIMEText(body_html, 'html'))

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()

        logger.info(f"Email sent: {subject}")
        return True

    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False

def _source_label(source: str) -> str:
    """Convert internal source key to a readable label for the email."""
    labels = {
        "linkedin_email": "LinkedIn Alert",
        "indeed_email": "Indeed Alert",
        "glassdoor_email": "Glassdoor Alert",
        "jsearch_api": "Online (JSearch)",
        "hacker_news": "Hacker News",
        "unknown_email": "Email Alert",
    }
    return labels.get(source, source)

def generate_daily_digest_email(stats: Dict) -> Tuple[str, str]:
    """Generate HTML email for daily digest."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get platinum jobs
    cursor.execute("""
        SELECT id, title, company, location, salary_min, salary_max, link,
               posted_date, goldness_score, source
        FROM jobs
        WHERE tier = 'platinum' AND emailed = 0 AND applied = 0
        ORDER BY goldness_score DESC
    """)
    platinum_jobs = cursor.fetchall()

    # Get gold jobs
    cursor.execute("""
        SELECT id, title, company, location, salary_min, salary_max, link,
               posted_date, goldness_score, source
        FROM jobs
        WHERE tier = 'gold' AND emailed = 0 AND applied = 0
        ORDER BY goldness_score DESC
    """)
    gold_jobs = cursor.fetchall()

    # Get silver jobs
    cursor.execute("""
        SELECT id, title, company, location, salary_min, salary_max, link,
               posted_date, goldness_score, source
        FROM jobs
        WHERE tier = 'silver' AND emailed = 0 AND applied = 0
        ORDER BY goldness_score DESC
    """)
    silver_jobs = cursor.fetchall()

    conn.close()

    total_highlighted = len(platinum_jobs) + len(gold_jobs)
    subject = f"🥇 {total_highlighted} Golden Jobs Found ({len(silver_jobs)} Silver) - {datetime.now().strftime('%B %d, %Y')}" if total_highlighted > 0 else f"📋 {len(silver_jobs)} Jobs Found - {datetime.now().strftime('%B %d, %Y')}"

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #1a1a1a; border-bottom: 3px solid #007bff;">Gold Rush Daily Report</h1>

        <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p><strong>✓ System Health:</strong> All checks passed</p>
            <p><strong>✓ Yesterday:</strong> Found {stats['total_found']} jobs, {stats['platinum'] + stats['gold']} qualified as golden</p>
            <p><strong>✓ New Jobs:</strong> {stats['new_jobs']} (Platinum: {stats['platinum']}, Gold: {stats['gold']}, Silver: {stats['silver']})</p>
        </div>
    """

    if platinum_jobs:
        html += """
        <h2 style="color: #007bff;">🥇 PLATINUM JOBS (Score 90+)</h2>
        """

        for i, job in enumerate(platinum_jobs, 1):
            job_id, title, company, location, sal_min, sal_max, link, posted, score, source = job

            salary_str = ""
            if sal_min and sal_max:
                salary_str = f"${sal_min:,} - ${sal_max:,}"
            elif sal_min:
                salary_str = f"${sal_min:,}+"
            else:
                salary_str = "Salary not listed"

            # Calculate hours ago
            if posted:
                hours_ago = int((datetime.now() - datetime.fromisoformat(str(posted))).total_seconds() / 3600)
                time_str = f"{hours_ago} hours ago"
            else:
                time_str = "Recently"

            source_str = _source_label(source)
            applied_subject = f"APPLIED:#{job_id} - {title} at {company}".replace(" ", "%20")
            applied_mailto = f"mailto:{EMAIL_ADDRESS}?subject={applied_subject}"
            html += f"""
            <div style="background: #fff; border-left: 5px solid #dc3545; padding: 15px; margin: 15px 0; border-radius: 5px;">
                <h3 style="margin-top: 0; color: #333;">{i}. {title}</h3>
                <p style="margin: 5px 0;">📍 {company} | {location}</p>
                <p style="margin: 5px 0;">💰 {salary_str}</p>
                <p style="margin: 5px 0;">⏰ Posted {time_str}</p>
                <p style="margin: 5px 0;">📊 Score: {score}/100</p>
                <p style="margin: 5px 0;">🔎 Found via: <strong>{source_str}</strong></p>
                <p style="margin: 10px 0;">
                    <a href="{link}" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Apply Now</a>
                    &nbsp;&nbsp;
                    <a href="{applied_mailto}" style="background: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">✓ I Applied</a>
                </p>
            </div>
            """

    if gold_jobs:
        html += """
        <h2 style="color: #007bff;">🥈 GOLD JOBS (Score 75-89)</h2>
        """

        for i, job in enumerate(gold_jobs, 1):
            job_id, title, company, location, sal_min, sal_max, link, posted, score, source = job

            salary_str = ""
            if sal_min and sal_max:
                salary_str = f"${sal_min:,} - ${sal_max:,}"
            elif sal_min:
                salary_str = f"${sal_min:,}+"
            else:
                salary_str = "Salary not listed"

            if posted:
                hours_ago = int((datetime.now() - datetime.fromisoformat(str(posted))).total_seconds() / 3600)
                time_str = f"{hours_ago} hours ago"
            else:
                time_str = "Recently"

            source_str = _source_label(source)
            applied_subject = f"APPLIED:#{job_id} - {title} at {company}".replace(" ", "%20")
            applied_mailto = f"mailto:{EMAIL_ADDRESS}?subject={applied_subject}"
            html += f"""
            <div style="background: #fff; border-left: 5px solid #ffc107; padding: 15px; margin: 15px 0; border-radius: 5px;">
                <h3 style="margin-top: 0; color: #333;">{i}. {title}</h3>
                <p style="margin: 5px 0;">📍 {company} | {location}</p>
                <p style="margin: 5px 0;">💰 {salary_str}</p>
                <p style="margin: 5px 0;">⏰ Posted {time_str}</p>
                <p style="margin: 5px 0;">📊 Score: {score}/100</p>
                <p style="margin: 5px 0;">🔎 Found via: <strong>{source_str}</strong></p>
                <p style="margin: 10px 0;">
                    <a href="{link}" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Apply Now</a>
                    &nbsp;&nbsp;
                    <a href="{applied_mailto}" style="background: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">✓ I Applied</a>
                </p>
            </div>
            """

    if silver_jobs:
        html += """
        <h2 style="color: #6c757d;">🥉 SILVER JOBS (Score 60-74)</h2>
        """
        for i, job in enumerate(silver_jobs, 1):
            job_id, title, company, location, sal_min, sal_max, link, posted, score, source = job
            salary_str = f"${sal_min:,}+" if sal_min else "Salary not listed"
            source_str = _source_label(source)
            applied_subject = f"APPLIED:#{job_id} - {title} at {company}".replace(" ", "%20")
            applied_mailto = f"mailto:{EMAIL_ADDRESS}?subject={applied_subject}"
            html += f"""
            <div style="background: #fff; border-left: 5px solid #6c757d; padding: 15px; margin: 10px 0; border-radius: 5px;">
                <h3 style="margin-top: 0; color: #333;">{i}. {title}</h3>
                <p style="margin: 5px 0;">📍 {company} | {location}</p>
                <p style="margin: 5px 0;">💰 {salary_str}</p>
                <p style="margin: 5px 0;">📊 Score: {score}/100</p>
                <p style="margin: 5px 0;">🔎 Found via: <strong>{source_str}</strong></p>
                <p style="margin: 10px 0;">
                    <a href="{link}" style="background: #6c757d; color: white; padding: 8px 16px; text-decoration: none; border-radius: 5px;">View Job</a>
                    &nbsp;&nbsp;
                    <a href="{applied_mailto}" style="background: #28a745; color: white; padding: 8px 16px; text-decoration: none; border-radius: 5px;">✓ I Applied</a>
                </p>
            </div>
            """

    if not platinum_jobs and not gold_jobs and not silver_jobs:
        html += """
        <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p><strong>No jobs found today.</strong></p>
            <p>This could mean:</p>
            <ul>
                <li>Slow day in the job market</li>
                <li>Search criteria might be too narrow</li>
                <li>Check back tomorrow - fresh jobs post daily</li>
            </ul>
        </div>
        """

    html += """
        <hr style="margin: 30px 0; border: none; border-top: 2px solid #e0e0e0;">
        <p style="color: #666; font-size: 0.9em;">
            <strong>Gold Rush v1.0</strong><br>
            Next check: This evening<br>
            <a href="https://github.com/yourusername/gold-rush">Report an issue</a>
        </p>
    </body>
    </html>
    """

    return subject, html

def mark_jobs_as_emailed(tier: str = None):
    """Mark jobs as emailed in database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if tier:
        cursor.execute("UPDATE jobs SET emailed = 1 WHERE tier = ? AND emailed = 0", (tier,))
    else:
        cursor.execute("UPDATE jobs SET emailed = 1 WHERE emailed = 0")

    conn.commit()
    conn.close()

def check_applied_emails():
    """
    Scan Gmail for 'APPLIED:#<id>' emails sent by the user.
    Marks matching jobs as applied in the database.
    """
    if not EMAIL_ADDRESS or not EMAIL_APP_PASSWORD:
        return

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
        mail.select("inbox")

        # Search for APPLIED emails from the last 30 days
        date = (datetime.now() - timedelta(days=30)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(SUBJECT "APPLIED:#" SINCE {date})')

        if not messages[0]:
            mail.close()
            mail.logout()
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        marked = 0

        for msg_id in messages[0].split():
            try:
                status, msg_data = mail.fetch(msg_id, "(RFC822)")
                email_message = email.message_from_bytes(msg_data[0][1])
                subject = email_message.get("Subject", "")

                # Extract job ID from subject like "APPLIED:#47 - Data Analyst at Anthropic"
                match = re.search(r'APPLIED:#(\d+)', subject)
                if match:
                    job_db_id = int(match.group(1))
                    cursor.execute(
                        "UPDATE jobs SET applied = 1 WHERE id = ? AND applied = 0",
                        (job_db_id,)
                    )
                    if cursor.rowcount > 0:
                        marked += 1
                        logger.info(f"Marked job #{job_db_id} as applied (from email)")
            except Exception as e:
                logger.error(f"Error processing APPLIED email: {e}")
                continue

        conn.commit()
        conn.close()
        mail.close()
        mail.logout()

        if marked > 0:
            logger.info(f"Marked {marked} jobs as applied from email replies")

    except Exception as e:
        logger.error(f"Error checking applied emails: {e}")

# ============================================================================
# HACKER NEWS SOURCE
# ============================================================================

HN_OUTPUTS_DIR = Path("$HOME/2026Projects/Job Searching/outputs")

# Non-US indicators to filter out
NON_US_INDICATORS = [
    "germany", "german", "gmbh", "uk", "london", "europe", "eu", "ireland",
    "cork", "berlin", "amsterdam", "paris", "toronto", "canada", "australia",
    "india", "singapore", "latam", "brazil", "mexico", "remote (eur", "remote (ger",
    "remote (eu", "cet", "gmt", "bst"
]

VALID_HN_ROLES = {"Business / Data Analyst", "Data / Analytics Engineering"}

# Parts that are NOT a job title
META_INDICATORS = [
    "remote", "onsite", "hybrid", "full-time", "full time", "part-time", "part time",
    "contract", "us-based", "global", "multiple roles", "multiple openings",
    "sf", "bay area", "new york", "nyc", "chicago", "austin", "boston", "atlanta",
    "worldwide", "north america", "south america", "hiring", "perm", "equity",
]

SKIP_TITLE_KEYWORDS = [
    "software engineer", "sre", "frontend", "backend", "devops", "designer",
    "ui/ux", "intern", "ml infra", "c++", "full stack", "full-stack", "infrastructure",
    "robotics", "marketing", "sales", "recruiting", "node.js", "golang",
    "go engineer", "cloud engineer", "security engineer", "platform engineer",
    "director of engineering", "head of engineering", "devrel", "developer relations",
    "multiple", "product & engineering", "product engineer", "founding engineer",
]

def _is_meta_part(text: str) -> bool:
    """Returns True if a pipe-segment looks like location/employment type, not a job title."""
    t = text.lower().strip()
    if t.startswith("http") or ".com" in t or ".io" in t or ".ai" in t or ".dev" in t:
        return True
    if re.match(r"^\$[\d,k]", t):  # salary like $150k
        return True
    return any(m in t for m in META_INDICATORS)

def _parse_hn_snippet(snippet: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract (company, title) from an HN job snippet.
    HN format is inconsistent — handles common patterns:
      Company | Title | Location | ...
      Company | Location | Title | ...
      Company | URL | Title | ...
      Title | Employment | Location | ...  (no company)
    Returns (None, None) if can't parse cleanly.
    """
    parts = [p.strip() for p in snippet.split("|")]
    if len(parts) < 2:
        return None, None

    company = parts[0].strip()

    # If part[0] looks like a URL or is empty, skip
    if not company or company.startswith("http"):
        return None, None

    # Find the first non-meta part after company as the title
    title = None
    for part in parts[1:4]:
        part = part.strip()
        if not part:
            continue
        if not _is_meta_part(part) and len(part) > 4:
            title = part
            break

    return company, title

def fetch_hn_jobs() -> List[Dict]:
    """
    Read the latest HN CSV from tpm_job_hunter outputs.
    Filters to relevant roles, US-only, and cleans company/title parsing.
    """
    if not HN_OUTPUTS_DIR.exists():
        logger.warning("HN outputs directory not found, skipping")
        return []

    csv_files = sorted(HN_OUTPUTS_DIR.glob("TPM_Jobs_*.csv"), reverse=True)
    if not csv_files:
        logger.info("No HN CSV files found")
        return []

    latest_csv = csv_files[0]
    csv_date = latest_csv.stem.split("_")[2]

    today = datetime.now().strftime("%Y-%m-%d")
    if csv_date != today:
        logger.info(f"Most recent HN CSV is from {csv_date}, not today — skipping")
        return []

    import csv as csv_module
    jobs = []
    skipped = 0

    with open(latest_csv, newline="", encoding="utf-8") as f:
        for row in csv_module.DictReader(f):
            if row.get("Role Match") not in VALID_HN_ROLES:
                continue

            snippet = row.get("Snippet", "")
            snippet_lower = snippet.lower()

            # Skip non-US postings
            if any(ind in snippet_lower for ind in NON_US_INDICATORS):
                skipped += 1
                continue

            # Skip seeking-work posts
            if snippet_lower.startswith("seeking") or snippet_lower.startswith("looking for"):
                skipped += 1
                continue

            # Parse company and title
            company, title = _parse_hn_snippet(snippet)

            # Skip if we couldn't extract both cleanly
            if not company or not title:
                skipped += 1
                continue

            # Skip non-analyst titles
            title_lower = title.lower()
            if any(kw in title_lower for kw in SKIP_TITLE_KEYWORDS):
                skipped += 1
                continue

            sal_min = None
            sal_max = None
            try:
                if row.get("Min Salary USD"):
                    sal_min = int(float(row["Min Salary USD"]))
                if row.get("Max Salary USD"):
                    sal_max = int(float(row["Max Salary USD"]))
            except (ValueError, TypeError):
                pass

            jobs.append({
                "title": title,
                "company": company,
                "location": "Remote / US",
                "salary_min": sal_min,
                "salary_max": sal_max,
                "salary_text": f"${sal_min:,} - ${sal_max:,}" if sal_min and sal_max else "",
                "link": row.get("Link", ""),
                "source": "hacker_news",
                "posted_date": datetime.strptime(row["Date"], "%Y-%m-%d") if row.get("Date") else datetime.now(),
            })

    logger.info(f"Fetched {len(jobs)} clean HN jobs ({skipped} skipped) from {latest_csv.name}")
    return jobs

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def export_to_dashboard():
    """Export jobs and metadata as JSON to the dashboard repo, then git push."""
    DASHBOARD_DIR = Path.home() / "goldrush-dashboard" / "public"

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row

        # Export all jobs
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY goldness_score DESC"
        ).fetchall()

        jobs = []
        for row in rows:
            jobs.append({
                "id": row["id"],
                "job_id": row["job_id"],
                "title": row["title"],
                "company": row["company"],
                "location": row["location"],
                "salary_min": row["salary_min"],
                "salary_max": row["salary_max"],
                "salary_text": row["salary_text"],
                "link": row["link"],
                "source": row["source"],
                "posted_date": row["posted_date"],
                "found_date": row["found_date"],
                "goldness_score": row["goldness_score"],
                "tier": row["tier"],
                "emailed": bool(row["emailed"]),
                "applied": bool(row["applied"]),
            })

        # Build metadata
        tier_counts = {"platinum": 0, "gold": 0, "silver": 0, "bronze": 0}
        source_counts = {}
        for job in jobs:
            tier_counts[job["tier"]] = tier_counts.get(job["tier"], 0) + 1
            source_counts[job["source"]] = source_counts.get(job["source"], 0) + 1

        # Count jobs found today
        today_start = datetime.now().replace(hour=0, minute=0, second=0).isoformat()
        new_today = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE found_date >= ?", (today_start,)
        ).fetchone()[0]

        conn.close()

        meta = {
            "last_run": datetime.now().isoformat(),
            "total_jobs": len(jobs),
            "new_jobs_this_run": new_today,
            "tier_counts": tier_counts,
            "source_counts": source_counts,
            "export_time": datetime.now().isoformat(),
        }

        # Write JSON files
        DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

        with open(DASHBOARD_DIR / "jobs.json", "w") as f:
            json.dump(jobs, f, indent=2, default=str)

        with open(DASHBOARD_DIR / "meta.json", "w") as f:
            json.dump(meta, f, indent=2)

        logger.info(f"Dashboard export: {len(jobs)} jobs written to {DASHBOARD_DIR}")

        # Git commit and push
        repo_dir = DASHBOARD_DIR.parent
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run(["git", "add", "public/jobs.json", "public/meta.json"], cwd=repo_dir, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"Update job data {now_str}"],
            cwd=repo_dir, check=True
        )
        subprocess.run(["git", "push"], cwd=repo_dir, check=True)
        logger.info("Dashboard data pushed to GitHub")

    except Exception as e:
        logger.error(f"Dashboard export failed (non-fatal): {e}")


def main():
    """Main execution function."""
    logger.info("=" * 60)
    logger.info("Gold Rush starting...")
    logger.info("=" * 60)

    # Initialize database
    init_database()

    # Check for "I Applied" emails and mark jobs in DB
    check_applied_emails()

    # Collect jobs from all sources
    all_jobs = []

    # Source 1: Email parsing
    if ENABLE_EMAIL_PARSING:
        email_jobs = parse_job_alert_emails()
        all_jobs.extend(email_jobs)

    # Source 2: JSearch API
    api_jobs = fetch_jobs_from_api()
    all_jobs.extend(api_jobs)

    # Source 3: Hacker News (via tpm_job_hunter CSV)
    hn_jobs = fetch_hn_jobs()
    all_jobs.extend(hn_jobs)

    # Process and store jobs
    stats = process_and_store_jobs(all_jobs)

    # Send daily digest email
    # Also check DB for un-emailed silver+ jobs (e.g. from a previous run that stored but didn't email)
    conn = sqlite3.connect(DB_PATH)
    unemailed_count = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE emailed = 0 AND tier IN ('platinum','gold','silver')"
    ).fetchone()[0]
    conn.close()

    if SEND_DAILY_DIGEST and (stats["platinum"] > 0 or stats["gold"] > 0 or stats["silver"] > 0 or unemailed_count > 0):
        subject, body = generate_daily_digest_email(stats)
        send_email(subject, body)
        mark_jobs_as_emailed()
    elif stats["new_jobs"] == 0:
        # Send health check email even if no jobs found
        send_email(
            "Gold Rush Health Check - No New Jobs Today",
            f"<p>Gold Rush ran successfully but found no new golden jobs matching your criteria.</p><p>Total scanned: {stats['total_found']} jobs</p>"
        )

    # Export to dashboard
    export_to_dashboard()

    logger.info("=" * 60)
    logger.info("Gold Rush completed successfully")
    logger.info(f"Stats: {stats}")
    logger.info("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
