# Gold Rush Dashboard

Static Vite + React + TypeScript dashboard for the [Gold Rush](../README.md) job-search pipeline. Reads `jobs.json` and `meta.json` from `public/` (written by the pipeline on each run) and renders a sortable, filterable view of scored jobs with localStorage-backed "applied" state.

## Stack

- Vite + React + TypeScript
- Tailwind CSS (terminal aesthetic — green-on-black)
- Client-side only; no backend
- Deployed on Vercel (static output from `npm run build`)

## Running locally

```bash
npm install
npm run dev
```

Create `.env` with:

```
VITE_DASHBOARD_PASSWORD=your_password_here
```

> ⚠️ This password is baked into the client bundle at build time. It's obfuscation, not authentication — don't rely on it to protect sensitive data.

## Data contract

The dashboard expects two JSON files in `public/`:

- **`jobs.json`** — array of scored job objects (title, company, score, source, url, etc.)
- **`meta.json`** — last-run timestamp + summary stats

The parent pipeline's `export_to_dashboard()` function in `gold_rush.py` is what writes these files and pushes to the dashboard repo.

## Build & deploy

```bash
npm run build     # outputs to dist/
vercel --prod     # or let Vercel auto-deploy from git push
```
