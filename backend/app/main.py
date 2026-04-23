"""FastAPI app for the DEI downloader.

Endpoints:
    GET  /api/health        - readiness probe
    GET  /api/catalog       - full indicator catalog (for frontend to render)
    POST /api/preview       - dry-run: counts rows per source without exporting
    POST /api/download      - returns an xlsx bundle for the selected pillars/years
    GET  /api/aei/preview   - counts rows available in AEI country panel
    GET  /api/aei/download  - xlsx download of AEI country panel
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator

from .catalog import CATALOG, Availability, Pillar
from .orchestrator import PILLAR_LABELS, PILLAR_ORDER, build_workbook, fetch

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

def _normalize_origin(value: str) -> str:
    """Accept either a bare hostname or a full URL and return a valid CORS origin.

    Render's `fromService property: hostport` gives us something like
    'dei-downloader-web.onrender.com' without the scheme. We need to prepend
    https:// so the origin matches the browser's Origin header.
    """
    value = value.strip().rstrip("/")
    if not value:
        return ""
    if value.startswith(("http://", "https://")):
        return value
    # Local dev shortcut: localhost never uses https
    if value.startswith("localhost") or value.startswith("127."):
        return f"http://{value}"
    return f"https://{value}"


CORS_ORIGINS = [
    normalized
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if (normalized := _normalize_origin(origin))
]

MIN_YEAR = int(os.getenv("MIN_YEAR", "2020"))
MAX_YEAR = int(os.getenv("MAX_YEAR", str(datetime.now().year)))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "DEI downloader starting. Year range %s-%s, CORS origins: %s",
        MIN_YEAR,
        MAX_YEAR,
        CORS_ORIGINS,
    )
    yield


app = FastAPI(
    title="DEI Downloader",
    version="1.0.0",
    description="Download underlying indicators for the Digital Evolution Index 2025.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class DownloadRequest(BaseModel):
    pillars: list[str] = Field(..., min_length=1, description="Pillars to include")
    start_year: int = Field(..., ge=2000, le=2100)
    end_year: int = Field(..., ge=2000, le=2100)
    countries: list[str] | None = Field(
        default=None,
        description="Optional ISO-3 codes to filter rows; None = all DEI countries",
    )
    indicator_keys: list[str] | None = Field(
        default=None,
        description="Optional catalog keys to restrict to; None = all in selected pillars",
    )

    @field_validator("pillars")
    @classmethod
    def _validate_pillars(cls, v: list[str]) -> list[str]:
        valid = {p.value for p in Pillar}
        bad = [p for p in v if p not in valid]
        if bad:
            raise ValueError(f"Unknown pillars: {bad}. Valid: {sorted(valid)}")
        return v

    @field_validator("countries")
    @classmethod
    def _validate_countries(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        # Normalize to uppercase ISO-3; strip blanks
        cleaned = [c.strip().upper() for c in v if c and c.strip()]
        if not cleaned:
            # Empty list after cleaning means "no countries" which is a user error;
            # treat as None (all countries) to avoid empty-xlsx surprises.
            return None
        return cleaned

    @field_validator("indicator_keys")
    @classmethod
    def _validate_indicator_keys(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        cleaned = [k.strip() for k in v if k and k.strip()]
        return cleaned or None

    def pillar_set(self) -> set[Pillar]:
        return {Pillar(p) for p in self.pillars}

    def country_set(self) -> set[str] | None:
        return set(self.countries) if self.countries else None

    def indicator_key_set(self) -> set[str] | None:
        return set(self.indicator_keys) if self.indicator_keys else None

    def validated_years(self) -> tuple[int, int]:
        start = max(self.start_year, MIN_YEAR)
        end = min(self.end_year, MAX_YEAR)
        if start > end:
            raise HTTPException(status_code=400, detail="start_year must be <= end_year")
        return start, end


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "year_range": {"min": MIN_YEAR, "max": MAX_YEAR},
        "catalog_size": len(CATALOG),
    }


@app.get("/api/catalog")
def get_catalog() -> dict[str, Any]:
    """Return the full indicator catalog, grouped by pillar."""
    grouped: dict[str, list[dict[str, Any]]] = {p.value: [] for p in PILLAR_ORDER}
    for ind in CATALOG:
        grouped[ind.pillar.value].append(
            {
                "key": ind.key,
                "name": ind.name,
                "component": ind.component,
                "source": ind.source,
                "source_code": ind.source_code,
                "availability": ind.availability.value,
                "unit": ind.unit,
                "notes": ind.notes,
                "manual_url": ind.manual_url,
                "earliest_year": ind.earliest_year,
                "latest_year": ind.latest_year,
                "publication_lag_years": ind.publication_lag_years,
                "sparse": ind.sparse,
            }
        )

    pillars_meta = [
        {"key": p.value, "label": PILLAR_LABELS[p], "indicators": grouped[p.value]}
        for p in PILLAR_ORDER
    ]

    source_counts: dict[str, dict[str, int]] = {}
    for ind in CATALOG:
        entry = source_counts.setdefault(
            ind.source,
            {"api": 0, "manual": 0, "subscription": 0},
        )
        entry[ind.availability.value] += 1

    return {
        "pillars": pillars_meta,
        "year_range": {"min": MIN_YEAR, "max": MAX_YEAR},
        "source_summary": source_counts,
        "availability_counts": {
            av.value: sum(1 for i in CATALOG if i.availability == av)
            for av in Availability
        },
    }


@app.get("/api/countries")
def get_countries() -> dict[str, Any]:
    """Return the list of DEI economies with ISO-3 codes and regions."""
    from .countries import DEI_COUNTRIES

    by_region: dict[str, list[dict[str, str]]] = {}
    for c in DEI_COUNTRIES:
        by_region.setdefault(c.region, []).append({"iso3": c.iso3, "name": c.name})

    # Sort countries alphabetically within each region
    for region in by_region:
        by_region[region].sort(key=lambda x: x["name"])

    return {
        "countries": [
            {"iso3": c.iso3, "name": c.name, "region": c.region} for c in DEI_COUNTRIES
        ],
        "by_region": by_region,
        "total": len(DEI_COUNTRIES),
    }


@app.post("/api/preview")
async def preview(req: DownloadRequest) -> dict[str, Any]:
    """Fetch and return counts without building the xlsx — cheap sanity check."""
    start, end = req.validated_years()
    result = await fetch(
        req.pillar_set(),
        start,
        end,
        countries=req.country_set(),
        indicator_keys=req.indicator_key_set(),
    )

    return {
        "year_range": {"start": start, "end": end},
        "total_rows": len(result.points),
        "sources": [
            {
                "source": s.source,
                "requested": s.requested,
                "fetched_rows": s.fetched_rows,
                "ok": s.ok,
                "message": s.message,
            }
            for s in result.statuses
        ],
        "rows_per_pillar": {
            p.value: sum(1 for pt in result.points if pt.pillar == p.value)
            for p in PILLAR_ORDER
            if p in req.pillar_set()
        },
    }


@app.post("/api/download")
async def download(req: DownloadRequest) -> Response:
    """Fetch all selected indicators and return an xlsx workbook."""
    start, end = req.validated_years()
    result = await fetch(
        req.pillar_set(),
        start,
        end,
        countries=req.country_set(),
        indicator_keys=req.indicator_key_set(),
    )
    xlsx_bytes = build_workbook(result, req.pillar_set(), start, end)

    pillar_slug = "-".join(sorted(p.value for p in req.pillar_set()))
    country_slug = ""
    if req.country_set():
        country_count = len(req.country_set())  # type: ignore[arg-type]
        country_slug = f"_{country_count}ctry"
    filename = f"dei-indicators_{pillar_slug}{country_slug}_{start}-{end}.xlsx"

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Total-Rows": str(len(result.points)),
        },
    )


# ==========================================================================
# Anthropic Economic Index — separate panel, not mixed with DEI pillars
# ==========================================================================

@app.get("/api/aei/preview")
async def aei_preview() -> dict[str, Any]:
    """Fetch AEI country panel and return a summary for the frontend."""
    from .sources import anthropic_aei

    rows = await anthropic_aei.fetch_country_rows()
    if not rows:
        return {
            "available": False,
            "message": "Anthropic Economic Index country CSV could not be fetched",
            "country_count": 0,
            "variables": [],
            "date_range": None,
        }

    countries = {r.country_iso3 for r in rows}
    variables_present = sorted({r.variable_key for r in rows})
    sample = rows[0]
    return {
        "available": True,
        "country_count": len(countries),
        "row_count": len(rows),
        "variables": [
            {"key": k, "label": anthropic_aei.COUNTRY_VARIABLES[k]}
            for k in variables_present
        ],
        "date_range": {
            "start": sample.date_start,
            "end": sample.date_end,
        },
        "release": "2025-09-15 (Uneven Geographic and Enterprise AI Adoption)",
        "license": "CC-BY 4.0",
        "source_url": "https://huggingface.co/datasets/Anthropic/EconomicIndex",
    }


@app.get("/api/aei/download")
async def aei_download() -> Response:
    """Return the AEI country panel as a pivoted xlsx."""
    from .sources import anthropic_aei

    rows = await anthropic_aei.fetch_country_rows()
    if not rows:
        raise HTTPException(
            status_code=503,
            detail="AEI country data could not be fetched from Hugging Face",
        )

    xlsx_bytes = anthropic_aei.build_workbook(rows)
    filename = "aei-country-panel_release-2025-09-15.xlsx"

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Country-Count": str(len({r.country_iso3 for r in rows})),
            "X-Row-Count": str(len(rows)),
        },
    )
