# Deploying to Render

Both the backend and frontend deploy to Render's free tier from a single
GitHub repo. The `render.yaml` blueprint at the repo root defines both
services, so connecting the repo is enough to spin up both at once.

## What you get

- **Backend**: FastAPI running on a Python 3.12 Web Service at
  `https://dei-downloader-api.onrender.com` (the exact subdomain will match
  the service name you pick in Render)
- **Frontend**: React/Vite static site at
  `https://dei-downloader-web.onrender.com`
- Auto-deploys on every push to `main`
- Automatic HTTPS certificates
- Zero CORS config or URL copying — the blueprint wires them to each other

## Free-tier caveat you should know about

The backend is a Python Web Service, which **sleeps after 15 minutes of
inactivity** on the free tier. The first request after sleep takes 30-60
seconds to wake up. For a portfolio piece this is fine — recruiters won't
churn on it, and subsequent requests are instant once awake.

Two ways around this if it bothers you later:
1. Upgrade the backend to the **Starter** plan ($7/month) — no sleep
2. Set up a cron job that pings `/api/health` every 10 minutes to keep it
   warm (Render's free cron service, or GitHub Actions, both work)

Static sites never sleep, so the frontend loads instantly regardless.

## Prerequisites

1. A GitHub account with this repo pushed to it
2. A Render account (free, signup at https://render.com)

## Step-by-step

### 1. Push your code to GitHub

From the project root:

```bash
git init
git add .
git commit -m "Initial DEI Downloader"
# create a new repo on github.com/new, then:
git remote add origin git@github.com:YOUR_USERNAME/dei-downloader.git
git branch -M main
git push -u origin main
```

Make sure `.gitignore` excludes `node_modules`, `__pycache__`, `dist`,
`.env.local`, and `.pytest_cache`. The `.gitignore` in this repo already
does that.

### 2. Connect the repo to Render

1. Log in to https://dashboard.render.com
2. Click **New +** → **Blueprint**
3. Connect your GitHub account if you haven't already
4. Pick the `dei-downloader` repo
5. Render reads `render.yaml` and shows a preview of both services
6. Click **Apply**

Render spins up both services. First deploy takes 4-6 minutes total (the
backend takes longest; npm builds are fast).

### 3. Verify each service

Once both services show green "Live" status in the dashboard:

**Backend health check**: visit `https://dei-downloader-api.onrender.com/api/health`
You should see `{"status":"ok","indicators_total":54}` or similar.

**Frontend**: visit `https://dei-downloader-web.onrender.com`
You should see the full DEI downloader UI, able to select pillars/countries
and download xlsx files.

If the first frontend load shows a "Could not load catalog" error, the
backend is probably cold-starting. Wait 30 seconds and reload.

### 4. Custom domains (optional)

Both services support custom domains on the free tier:

1. In the service's dashboard, click **Settings** → **Custom Domain**
2. Add your domain (e.g. `dei.suyogpokhrel.com`)
3. Add the CNAME record your DNS provider asks for
4. Render provisions an SSL cert automatically

If you add a custom domain to the frontend, you'll also want to add it to
the backend's `CORS_ORIGINS` env var (in the backend service settings)
so browser requests from the new domain aren't blocked. Comma-separate
multiple origins.

## What happens on every push

When you push to `main`:

1. Render detects the commit (GitHub webhook)
2. Backend redeploys: runs `pip install -r requirements.txt`, restarts Uvicorn
3. Frontend redeploys: runs `npm ci && npm run build`, publishes `dist/`
4. Both services are live with the new code in 2-3 minutes

Failed builds don't affect the live version — the old deploy keeps serving
until the new one succeeds.

## Troubleshooting

**Frontend shows "Could not load catalog" for longer than 60 seconds**
The backend is either crashing or taking longer than expected to wake up.
Open the backend service's **Logs** tab in Render to see the startup errors.
Common issues:
- Missing Python dependency: add it to `backend/requirements.txt`
- Python version mismatch: confirm `PYTHON_VERSION` env var is `3.12.3`

**CORS errors in the browser console**
The backend's `CORS_ORIGINS` env var is either wrong or wasn't populated.
In the backend service's **Environment** tab, confirm `CORS_ORIGINS` is
set to the frontend's hostname (e.g. `dei-downloader-web.onrender.com`).
If you used the blueprint, this should happen automatically; if you set
up services manually, you need to add it by hand.

**AEI panel always shows "AEI data unreachable"**
Hugging Face file access is rate-limited. If your backend has been cold
and the CSV fetch times out, wait a minute and reload. If it's persistent,
check the backend logs for the real HTTP status code.

**"Service suspended due to free tier limits"**
Free tier gives 750 hours/month of combined Web Service runtime. If you're
running multiple projects you might exhaust this; upgrade to Starter or
pause other services in your Render account.

## File reference

- `render.yaml` — blueprint defining both services. Edit `region:` if you
  want something other than Oregon.
- `backend/requirements.txt` — Python deps. Render installs these on deploy.
- `frontend/package.json` — Node deps. Render runs `npm ci` to install.
- `backend/app/main.py` — reads `CORS_ORIGINS`, `MIN_YEAR`, `MAX_YEAR` from env.
- `frontend/src/lib/api.ts` — reads `VITE_API_BASE` at build time.
