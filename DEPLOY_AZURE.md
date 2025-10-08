Azure deployment guide

Overview
- Function App (timer trigger) aggregates daily and writes JSON to Blob.
- Web App (Flask on App Service) reads `feeds/latest.json` from Blob and renders the UI.

Prereqs
- Resources created (your names in parentheses):
  - Storage account (`aiskinfeedbbb9`)
  - Function App (`unified-feed`) with Application Insights
  - App Service Plan (`ASP-aiskinfeed-8586`) + Web App for Flask (create if not yet)

Repo layout
- Web app: `unified_feed_app.py`, `templates/`
- Aggregator shared module: `aggregator.py`
- Azure Function: `azure_function/` with `aggregate_feed/`

App settings (both apps)
- `FEED_CONTAINER=feeds`
- `FEED_BLOB_NAME=latest.json`

Web App settings (App Service)
- Option A (simple): `AZURE_STORAGE_CONNECTION_STRING` = storage connection string of `aiskinfeedbbb9`.
- Option B (managed): `BLOB_ACCOUNT_URL` = `https://<account>.blob.core.windows.net` and enable system-assigned identity, then grant it Storage Blob Data Reader on the storage account.
- Email (optional for /send-test-email): `RECIPIENT_EMAIL`, `EMAIL_ADDRESS`, `EMAIL_PASSWORD`, `SMTP_SERVER`, `SMTP_PORT`.
- Startup command (Linux): `gunicorn -b 0.0.0.0:8000 unified_feed_app:app`

Function App settings
- Uses `AzureWebJobsStorage` automatically; no extra connection needed.
- Optional overrides: `FEED_CONTAINER`, `FEED_BLOB_NAME`.
- Timer schedule is set in `azure_function/aggregate_feed/function.json`: `0 0 4 * * *` (04:00 UTC daily).
- Live source API credentials (set only on the Function App):
  - Reddit (PRAW):
    - `REDDIT_CLIENT_ID`
    - `REDDIT_CLIENT_SECRET`
    - Optional: `REDDIT_ACCOUNT` (username), `REDDIT_PASSWORD` (script auth)
    - Optional: `REDDIT_USER_AGENT` (defaults to `ai-skin-feed/1.0 by <username>`)
  - Twitter/X API v2:
    - Prefer: `TWITTER_BEARER_TOKEN`
    - Fallback: `TWITTER_API_KEY` + `TWITTER_API_KEY_SECRET` (auto-derives bearer)
  - Notes: Instagram is currently disabled by request. Each source is optional; if none are configured, the function falls back to `social_feed_combined.json` packaged in the app.

Create container
1) In Storage account, create container `feeds` (private).

Deploy Function App (CLI)
1) From repo root, install function dependencies locally (optional for build):
   `pip install -r azure_function/requirements.txt`
2) If using Azure Functions Core Tools:
   - `cd azure_function`
   - `func azure functionapp publish unified-feed --python`

Deploy Web App (CLI)
1) Ensure `requirements.txt` includes Azure SDKs (already updated).
2) Zip deploy or CI/CD:
   - Zip: `zip -r app.zip unified_feed_app.py templates aggregator.py requirements.txt`
   - `az webapp deploy --resource-group <rg> --name <webapp-name> --src-path app.zip --type zip`
3) Set Startup Command: `gunicorn -b 0.0.0.0:8000 unified_feed_app:app`

RBAC for Managed Identity (if using BLOB_ACCOUNT_URL)
1) Enable system-assigned identity for Web App and Function App.
2) In Storage account IAM, add role assignments:
   - Web App: Storage Blob Data Reader
   - Function App: Storage Blob Data Contributor

Validation
- After the timer runs (or trigger locally), you should see `feeds/latest.json` in the container.
- Visit your Web App root; it should render the Blob-backed feed. If Blob is missing, it falls back to `social_feed_combined.json`.

Local development
- Web app: `pip install -r requirements.txt && python unified_feed_app.py` then browse to `http://localhost:5001`.
- Function: `pip install -r azure_function/requirements.txt` and `func start` inside `azure_function/`.
