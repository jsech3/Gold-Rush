# Gold Rush Setup Guide

**Time Required:** 30 minutes
**Difficulty:** Easy (copy/paste commands)

---

## Prerequisites

✅ Mac running macOS (for launchd scheduling)
✅ Python 3.10+ installed
✅ Gmail account
✅ JSearch API key (you already have this from Job Tracking Dashboard)

---

## Step 1: Install Dependencies (5 minutes)

Open Terminal and navigate to the Job Searching folder:

```bash
cd "$HOME/Job Searching"
```

Install required Python packages:

```bash
pip3 install requests beautifulsoup4 python-dotenv
```

**Expected output:** "Successfully installed..." messages

---

## Step 2: Get Gmail App Password (10 minutes)

**Why:** Google doesn't allow apps to use your real password. You need to generate a special "app password."

**Steps:**

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)

2. You might need to enable 2-Factor Authentication first if you haven't:
   - Go to [myaccount.google.com/security](https://myaccount.google.com/security)
   - Click "2-Step Verification" → Follow setup

3. Once 2FA is enabled, go back to App Passwords page

4. Under "Select app" → Choose "Mail"

5. Under "Select device" → Choose "Mac"

6. Click "Generate"

7. **Copy the 16-character password** (format: xxxx xxxx xxxx xxxx)
   - Save this - you'll need it in Step 3

---

## Step 3: Configure Environment Variables (5 minutes)

Create the configuration file:

```bash
cd "$HOME/Job Searching"
touch config.env
open -a TextEdit config.env
```

Paste this into `config.env` and fill in YOUR details:

```bash
# Email Settings
EMAIL_ADDRESS=your.email@gmail.com
EMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx  # From Step 2

# JSearch API (copy from your Job Tracking Dashboard .env)
JSEARCH_API_KEY=your_rapidapi_key_here
JSEARCH_API_HOST=jsearch.p.rapidapi.com

# Job Search Preferences
TARGET_TITLES=Technical Product Manager,Product Manager - Data,Product Manager - Analytics,Senior Product Analyst,Data Product Manager
TARGET_LOCATIONS=San Francisco,Remote,Bay Area,Palo Alto,Mountain View
MIN_SALARY=100000
PREFERRED_SALARY=120000

# Notification Settings
SEND_DAILY_DIGEST=true
SEND_IMMEDIATE_PLATINUM=true
DIGEST_TIME=07:00

# API Usage Limits
MAX_JSEARCH_CALLS_PER_DAY=6
ENABLE_EMAIL_PARSING=true

# Company Preferences
PREFERRED_COMPANIES=Stripe,Figma,Notion,Databricks,Snowflake,Retool,Airtable,Linear,Vercel,Ramp,Plaid
AVOID_COMPANIES=
```

**To get your JSearch API key:**

```bash
cd "$HOME/Job Tracking Dashboard"
cat .env | grep JSEARCH
```

Copy the value after `VITE_JSEARCH_API_KEY=` and paste it into Gold Rush's `config.env`

**Save and close the file.**

---

## Step 4: Set Up Job Alerts on LinkedIn/Indeed (10 minutes)

### LinkedIn Job Alerts

1. Go to [linkedin.com/jobs](https://linkedin.com/jobs)

2. Search for: "Technical Product Manager"
   - Location: "San Francisco, CA"
   - Click "Set Alert" (bell icon)
   - Frequency: **Daily**

3. Repeat for:
   - "Product Manager Data" in "Remote"
   - "Senior Product Analyst" in "San Francisco, CA"
   - "Product Manager Analytics" in "Remote"

### Indeed Job Alerts

1. Go to [indeed.com](https://indeed.com)

2. Search for: "Technical Product Manager"
   - Location: "San Francisco, CA"
   - Click "Email me jobs like these"
   - Frequency: **Daily**

3. Repeat for:
   - "Product Manager Data" in "Remote"
   - "Senior Product Analyst" in "Bay Area, CA"

**Important:** Use the SAME email address you configured in Step 3.

---

## Step 5: Test the Script (2 minutes)

Run the script manually to make sure it works:

```bash
cd "$HOME/Job Searching"
python3 gold_rush.py
```

**Expected output:**

```
============================================================
Gold Rush starting...
============================================================
INFO - Database initialized successfully
INFO - Found 0 job alert emails to parse  # Normal - you just set up alerts
INFO - JSearch API call: Technical Product Manager in San Francisco
INFO - JSearch API returned 10 jobs
INFO - Total jobs from JSearch API: 25
INFO - Processed 25 new jobs, 0 duplicates
INFO - Email sent: 🥇 5 Golden Jobs Found - February 7, 2026
============================================================
Gold Rush completed successfully
Stats: {'total_found': 25, 'new_jobs': 25, ...}
============================================================
```

**Check your email!** You should have received an email with golden jobs.

**If you get errors:**
- Check `logs/errors.log` for details
- Common issues:
  - Wrong Gmail app password → Regenerate in Step 2
  - JSearch API key invalid → Check Step 3
  - Missing dependencies → Run `pip3 install` again from Step 1

---

## Step 6: Schedule Automatic Runs (5 minutes)

Create the launchd configuration file:

```bash
cd "$HOME/Job Searching"
touch com.yourname.gold_rush.plist
open -a TextEdit com.yourname.gold_rush.plist
```

Paste this into the file:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.yourname.gold_rush</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$HOME/Job Searching/gold_rush.py</string>
    </array>

    <key>StartCalendarInterval</key>
    <array>
        <dict>
            <key>Hour</key>
            <integer>7</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
        <dict>
            <key>Hour</key>
            <integer>19</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
    </array>

    <key>StandardOutPath</key>
    <string>$HOME/Job Searching/logs/launchd.out.log</string>

    <key>StandardErrorPath</key>
    <string>$HOME/Job Searching/logs/launchd.err.log</string>

    <key>WorkingDirectory</key>
    <string>$HOME/Job Searching</string>

    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
```

**What this does:**
- Runs Gold Rush at **7:00 AM** (morning digest)
- Runs Gold Rush at **7:00 PM** (evening check)
- Logs output to `logs/` folder

**Save and close the file.**

**Install the scheduler:**

```bash
# Copy to LaunchAgents folder
cp com.yourname.gold_rush.plist ~/Library/LaunchAgents/

# Load the job (this starts it immediately and schedules future runs)
launchctl load ~/Library/LaunchAgents/com.yourname.gold_rush.plist

# Verify it's running
launchctl list | grep gold_rush
```

**Expected output:** `82756	0	com.yourname.gold_rush`

---

## Step 7: Verify Everything Works (2 minutes)

**Check logs:**

```bash
cd "$HOME/Job Searching"

# View main log
tail -20 logs/gold_rush.log

# Check for errors
tail -20 logs/errors.log
```

**Check database:**

```bash
sqlite3 gold_rush.db "SELECT COUNT(*) FROM jobs"
```

Should show number of jobs found (e.g., `25`)

**Check email:**
- You should have received the daily digest
- If it went to spam, mark as "Not Spam" and whitelist your email address

---

## You're Done! 🎉

### What Happens Next:

**Tomorrow at 7:00 AM:**
- Script runs automatically
- Checks Gmail for LinkedIn/Indeed alerts from overnight
- Makes JSearch API calls for fresh jobs
- Emails you 5-10 golden jobs
- You apply to top 3 before most people wake up

**Tomorrow at 7:00 PM:**
- Script runs again
- Catches jobs posted during the day
- Emails you evening update

### Daily Workflow:

1. **7:05 AM** - Check email for golden jobs
2. **7:15 AM** - Apply to top 3 platinum jobs (10 min)
3. **7:00 PM** - Check evening email for new jobs
4. **Evening** - Apply to another 2-3 jobs (10 min)

**Total time:** 20 min/day to apply to 5-6 golden jobs

---

## Troubleshooting

### No email received?

```bash
# Check if script ran
tail -50 logs/gold_rush.log

# Check if scheduler is loaded
launchctl list | grep gold_rush

# If not loaded, reload it
launchctl load ~/Library/LaunchAgents/com.yourname.gold_rush.plist
```

### Email went to spam?

1. Go to Gmail spam folder
2. Find the Gold Rush email
3. Click "Not Spam"
4. Create filter: From `your.email@gmail.com` → Never send to spam

### API rate limit exceeded?

Edit `config.env`, change:
```bash
MAX_JSEARCH_CALLS_PER_DAY=4  # Reduce from 6 to 4
```

Then:
```bash
launchctl unload ~/Library/LaunchAgents/com.yourname.gold_rush.plist
launchctl load ~/Library/LaunchAgents/com.yourname.gold_rush.plist
```

### Want to run manually?

```bash
cd "$HOME/Job Searching"
python3 gold_rush.py
```

### Want to stop the scheduler?

```bash
launchctl unload ~/Library/LaunchAgents/com.yourname.gold_rush.plist
```

To restart:
```bash
launchctl load ~/Library/LaunchAgents/com.yourname.gold_rush.plist
```

---

## Next Steps

**Week 1:**
- Monitor daily emails
- Apply to platinum jobs within 6 hours
- Track your response rate (should improve)

**Week 2:**
- Fine-tune `config.env` preferences
- Add/remove target titles if needed
- Adjust `PREFERRED_COMPANIES` list

**Week 3+:**
- Minimal maintenance
- Just collect golden jobs daily
- Land that full-time role 🚀

---

## Support

**Logs location:**
- `$HOME/Job Searching/logs/`

**Database location:**
- `$HOME/Job Searching/gold_rush.db`

**Need help?**
- Check logs first: `tail -50 logs/gold_rush.log`
- Check errors: `tail -50 logs/errors.log`
- Email yourself: [your.email@gmail.com](mailto:your.email@gmail.com)

**You've got this. Go get those golden jobs.**
