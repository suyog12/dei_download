# DEI Downloader

A web app for bundling the underlying indicators of the Tufts
[Digital Evolution Index 2025](https://digitalplanet.tufts.edu/digitalevolutionindex2025/)
into a single spreadsheet download. Select pillars, pick a year range,
click download.

The Tufts DEI itself is a scored, weighted composite built from 184 indicators
across four pillars. This tool does **not** reproduce the DEI scores — those
are Tufts's proprietary computation and depend on paid sources (Mastercard,
Akamai, Euromonitor, EIU, GWI, PCRI). What it does do is pull the **free,
public raw indicators** behind those pillars from authoritative APIs, plus
document the manual/subscription sources with links so you know where to get them.

## Architecture

```
dei-downloader/
├── backend/               FastAPI
│   ├── app/
│   │   ├── catalog.py           38 API + 14 manual + 2 sub indicators
│   │   ├── countries.py         125 DEI economies with ISO-3 + regions
│   │   ├── orchestrator.py      parallel dispatch + xlsx builder
│   │   ├── main.py              /api routes
│   │   └── sources/
│   │       ├── worldbank.py     WDI + Findex + WGI + WIPO + UNESCO
│   │       ├── owid.py          Our World in Data Chart API
│   │       └── imf.py           IMF DataMapper (WEO + fiscal)
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
│
└── frontend/              React + Vite + TypeScript
    ├── src/
    │   ├── App.tsx              main UI
    │   ├── lib/api.ts           typed client for the backend
    │   └── styles.css           editorial research aesthetic
    ├── package.json
    └── .env.example
```

### Why this shape

The browser can't safely hold secrets in a `.env`, and CORS blocks most of the
relevant data APIs from a browser anyway. The backend keeps credentials
server-side, handles concurrent fetching, and does the xlsx assembly with
pandas-free openpyxl so the container stays small. The frontend is a single
page that talks to the backend over JSON.

## Data sources

All API-tier sources listed here are free, require no credentials, and have been
verified to work against live endpoints:

| Source                               | Pillars covered            | Access     | Notes                                         |
| ------------------------------------ | -------------------------- | ---------- | --------------------------------------------- |
| World Bank WDI                       | Supply, Demand, Innovation | API        | Deepest country coverage                      |
| World Bank Global Findex             | Demand                     | API        | Sparse: 2011, 2014, 2017, 2021, 2024          |
| Worldwide Governance Indicators      | Institutional              | API        | 2-year publication lag                        |
| World Bank / UNESCO                  | Innovation                 | API        | R&D, tertiary enrolment                       |
| World Bank / WIPO                    | Innovation                 | API        | Patent applications                           |
| Our World in Data Chart API          | Institutional, Supply      | API        | Re-hosts Freedom House, CPI, V-Dem            |
| IMF DataMapper                       | Demand, Institutional      | API        | WEO includes forward projections; UA required |
| ITU DataHub                          | Supply                     | manual     | No public API; CSV export from web portal     |
| OECD Data Explorer                   | Innovation, Supply         | manual     | Free SDMX API exists but schema is complex; use web portal |
| UN SDG Database                      | Supply, Demand             | manual     | REST API exists but not reliably stable       |
| UNCTADstat                           | Innovation                 | manual     | API schema shifts; use web portal             |
| UN E-Government Survey               | Institutional              | manual     | Biennial; download from UN portal             |
| Open Data Watch ODIN                 | Institutional              | manual     | Annual CSV from odin.opendatawatch.com        |
| Ookla Open Data                      | Supply                     | manual     | Parquet tiles on AWS; heavy                   |
| GSMA Mobile Connectivity Index       | Supply                     | manual     | Free registration required                    |
| Euromonitor Passport                 | Demand                     | library    | W&M Swem Library subscription                 |
| Economist Intelligence Unit          | Institutional              | library    | EIU login required                            |

Manual and library sources appear in the UI as instructions, not as
auto-fetches. ITU, OECD, UN SDG, and UNCTAD all publish the same kind of data
that World Bank re-publishes under its IT.* and governance series, so for most
DEI-relevant questions, the World Bank entries give you what you need.

### Year coverage and soft greyout

Each indicator in the catalog carries `earliest_year` and `latest_year`
metadata. When you pick a year range outside an indicator's coverage window,
the UI greys it out with a tooltip explaining why. Your selection is preserved —
widen the range and it lights up again. Sparse series like Findex are never
greyed out for arbitrary years since the user may legitimately request a year
between waves.

### What happened to the other API sources?

Earlier versions of this project attempted to fetch from ITU, OECD, UN SDG,
UNCTAD, and Anthropic Economic Index programmatically. In practice:

- **ITU** — no public REST API exists; the `api.datahub.itu.int` endpoint I
  originally used was incorrect. ITU publishes data only via their DataHub
  web portal.
- **OECD** — the SDMX API is real but schema-heavy; dataflow IDs change
  frequently enough that a hardcoded catalog is fragile. The web portal is
  more reliable for ad-hoc pulls.
- **UN SDG** — the REST API exists but has ambiguous pagination and
  inconsistent response shapes per indicator.
- **UNCTADstat** — schema drift across releases makes programmatic access
  unreliable.
- **Anthropic Economic Index** — this dataset publishes conversation-level
  usage analysis, not country-level time-series indicators, so it doesn't
  fit the DEI pillar structure.

If you need data from any of these sources, use the `manual_url` link in the
catalog panel to pull the CSV yourself and merge it with the World Bank
download.

## Running locally

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                    # optional, defaults are fine
uvicorn app.main:app --reload --port 8000
```

Smoke test:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/catalog | jq '.pillars | length'   # → 4
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api/*` to the
backend on `:8000`.

### Running tests

```bash
cd backend
pytest -m 'not live'           # offline tests (7 tests)
pytest -m live                 # hits World Bank API
```

## Deploying

- **Backend**: any Python host with outbound HTTPS. Fly.io, Railway, Render,
  or a small AWS Lambda behind API Gateway all work. Set `CORS_ORIGINS` to
  the frontend URL. The app is stateless; scale horizontally.
- **Frontend**: `npm run build` produces static files in `frontend/dist/`.
  Drop them on Vercel, Netlify, Cloudflare Pages, or S3 + CloudFront. Set
  `VITE_API_BASE` to the backend URL at build time if the frontend isn't
  proxying through the same origin.

## Extending the catalog

Add a new indicator by appending an entry to `CATALOG` in
`backend/app/catalog.py`:

```python
Indicator(
    key="unique_snake_case_key",
    name="Human-readable name with units",
    pillar=Pillar.SUPPLY,          # or DEMAND / INSTITUTIONAL / INNOVATION
    component="Access Infrastructure",  # roll-up used in Tufts's taxonomy
    source="World Bank",           # must match a dispatch key in orchestrator
    source_code="IT.NET.USER.ZS",  # source-specific series code
    availability=Availability.API,
    unit="%",
)
```

The test suite enforces two invariants: every indicator key is unique, and
every `availability=API` indicator has a registered dispatch module. Adding
a new source family means (a) writing a new module in `app/sources/`,
(b) adding it to `API_DISPATCH` in `orchestrator.py`, and (c) adding its
name to `known_sources` in `tests/test_basics.py`.

## Known limitations

- **The sandbox where this was prototyped blocks outbound network**, so the
  live tests (`-m live`) can't run here. They're included for when you run
  the app against real endpoints. The offline tests exercise the parsing
  logic with a fixture matching the real World Bank JSON shape.
- **The Anthropic Economic Index fetcher tries multiple candidate file paths**
  because Anthropic renames files across releases. If all candidates 404, the
  source status will show "empty" in the preview; update the paths in
  `anthropic_aei.py` to the current release.
- **Euromonitor mobile e-commerce is central to Tufts's DEI but is not free.**
  There is no workaround; access it through your university library.
