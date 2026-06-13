# No-Website Outreach Pipeline

Find local businesses that have **no website** via the Google Places API (New),
draft a personalized outreach email for each with the Claude API, and send them
through a guarded, dry-run-by-default send pipeline.

## What it does

1. **discover** — Text-searches Places API (New), keeps only businesses with no
   `websiteUri`, and writes them to `data/leads.csv`.
2. **draft** — For each lead, generates a personalized subject + body with Claude.
3. **send** — Reads `data/leads.csv` and sends outreach. **Dry-run by default.**

> **Sourcing caveat:** Places API (New) returns name, category, address, phone,
> and website — **not email**. So discovered leads have a phone but an *empty
> email* column. The send step **skips empty-email rows by design**; the email
> column is meant to be filled by a human (or a future enrichment step) before
> any sending is possible. No scraping, no third-party enrichment is included.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in keys
```

### Required configuration

| Key | Used by | Notes |
|-----|---------|-------|
| `GOOGLE_MAPS_API_KEY` | discover | **Billing-enabled** GCP key with **Places API (New)** enabled. The request sends a mandatory `X-Goog-FieldMask` header; without billing/enablement the API returns HTTP 400/403. |
| `ANTHROPIC_API_KEY` | draft | Claude API key. |
| `ANTHROPIC_MODEL` | draft | Defaults to `claude-haiku-4-5-20251001` (cheap/fast). |
| `DRY_RUN` | send | Defaults to `true`. **Keep it true** until legal sign-off. |
| `RATE_LIMIT` | send | Seconds between real sends. |
| SMTP_* / FROM_* | send | Only needed when `DRY_RUN=false`. |
| `SENDER_POSTAL_ADDRESS`, `UNSUBSCRIBE_URL` | send | CAN-SPAM footer; required for real sends. |

## Usage

```bash
# 1. Discover no-website businesses
python -m src.cli discover "plumbers in Austin TX" --lat 30.27 --lng -97.74 --radius-m 20000

# 2. Draft personalized emails into the CSV
python -m src.cli draft

# 3a. Dry run (default) — prints what would send, sends nothing
python -m src.cli send

# 3b. Real send — only after filling emails AND legal sign-off
python -m src.cli send --no-dry-run     # also requires DRY_RUN=false in env

# Combined discover + draft
python -m src.cli pipeline "barbers in Dallas TX"
```

Run `python -m src.cli send --help` to confirm the dry-run default.

## Transport choice

The send step uses **SMTP via the Python standard library** (`smtplib`),
chosen over the Gmail API to avoid an OAuth dependency. Swap the transport in
`src/send.py` (`_send`/`send_pipeline`) if you prefer Gmail API or a provider SDK.

## Compliance — read before sending

Cold B2B email is **regulated**. Before setting `DRY_RUN=false`:

- **US (CAN-SPAM):** requires accurate headers, a non-deceptive subject, a valid
  physical postal address, and a working unsubscribe mechanism. This pipeline
  appends the address + unsubscribe footer and blocks deceptive subjects, but
  **you** must supply a real address and a functioning unsubscribe link.
- **EU (GDPR / ePrivacy):** unsolicited B2B email is restricted and in some
  member states (e.g. Germany) effectively prohibited without prior consent.
- **Get human legal sign-off** for your jurisdiction and target list before
  enabling real sends.

The send pipeline also honors `data/suppression.csv` (one email per line) and
never sends to suppressed or empty addresses.

## Places ToS

Store only the fields needed for outreach and respect the Places API caching /
retention limits. This project requests a minimal field mask for that reason.

## Development

```bash
python -m pytest -q          # all tests run offline (external APIs mocked)
ruff check .
black --check .
```
