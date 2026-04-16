# Product Requirements Document: TPM Job Scraper
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
