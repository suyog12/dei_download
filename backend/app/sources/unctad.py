"""UNCTAD Data Centre fetcher.

UNCTAD publishes its data through the API at:
    https://unctadstat-api.unctad.org/api/reportMetadata/...
    https://unctadstat-api.unctad.org/api/data/US.SoSICT.{indicator_id}

Unlike WB/IMF, UNCTADstat's API is less well-documented and the schema has
historically changed. We treat failures as "source unavailable" and return []
with a warning, the same pattern as ITU.

For DEI purposes the most relevant UNCTAD series are ICT-sector trade:
    - ICT goods exports as % of total exports
    - ICT services exports as % of total services exports
    - Digitally-deliverable services exports

These overlap with WB series already in the catalog but UNCTAD offers better
coverage for some developing economies and more recent year availability.

Catalog convention: `source_code` is the UNCTAD series ID.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from ..catalog import Indicator
from .base import DataPoint

logger = logging.getLogger(__name__)

UNCTAD_BASE = "https://unctadstat-api.unctad.org/api/data"
UA = "DEI-Downloader/1.0"


async def _fetch_one(
    client: httpx.AsyncClient, ind: Indicator, start_year: int, end_year: int
) -> list[DataPoint]:
    params = {
        "timePeriod": f"{start_year}-{end_year}",
        "format": "json",
    }
    url = f"{UNCTAD_BASE}/{ind.source_code}"

    try:
        resp = await client.get(
            url,
            params=params,
            headers={"Accept": "application/json", "User-Agent": UA},
            timeout=45.0,
        )
    except httpx.RequestError as exc:
        logger.warning("UNCTAD request error for %s: %s", ind.key, exc)
        return []

    if resp.status_code != 200:
        logger.warning("UNCTAD %s returned HTTP %s", ind.key, resp.status_code)
        return []

    try:
        payload: Any = resp.json()
    except ValueError:
        logger.warning("UNCTAD %s returned non-JSON", ind.key)
        return []

    # UNCTAD responses vary in shape across endpoints; normalize to a list of rows
    rows: list[dict[str, Any]] = []
    if isinstance(payload, list):
        rows = [r for r in payload if isinstance(r, dict)]
    elif isinstance(payload, dict):
        for key in ("data", "observations", "rows", "series"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                rows = [r for r in candidate if isinstance(r, dict)]
                break

    if not rows:
        return []

    out: list[DataPoint] = []
    for row in rows:
        # Try several common field names for the country code
        iso3 = (
            row.get("iso3")
            or row.get("countryISO3")
            or row.get("economyISO3")
            or row.get("REF_AREA")
            or ""
        ).upper()
        if len(iso3) != 3:
            continue

        # Year
        year_raw = (
            row.get("year")
            or row.get("timePeriod")
            or row.get("TIME_PERIOD")
            or row.get("period")
        )
        try:
            year = int(str(year_raw).split("-")[0])
        except (TypeError, ValueError):
            continue
        if year < start_year or year > end_year:
            continue

        # Value
        raw = row.get("value") or row.get("OBS_VALUE") or row.get("obsValue")
        try:
            value = float(raw) if raw not in (None, "", "NaN") else None
        except (TypeError, ValueError):
            value = None

        out.append(
            DataPoint(
                indicator_key=ind.key,
                indicator_name=ind.name,
                pillar=ind.pillar.value,
                component=ind.component,
                source=ind.source,
                country_iso3=iso3,
                country_name=row.get("countryLabel") or row.get("economyLabel") or "",
                year=year,
                value=value,
                unit=ind.unit,
            )
        )

    return out


async def fetch_indicators(
    indicators: list[Indicator], start_year: int, end_year: int
) -> list[DataPoint]:
    if not indicators:
        return []

    semaphore = asyncio.Semaphore(2)
    out: list[DataPoint] = []

    async with httpx.AsyncClient() as client:
        async def _bound(ind: Indicator) -> list[DataPoint]:
            async with semaphore:
                return await _fetch_one(client, ind, start_year, end_year)

        results = await asyncio.gather(*[_bound(ind) for ind in indicators])
        for chunk in results:
            out.extend(chunk)

    return out
