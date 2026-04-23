"""World Bank Indicators API fetcher.

One endpoint, three data families:
    - WDI series (IT.*, NY.*, IP.*, etc.)
    - Findex series (FX.*)
    - Worldwide Governance Indicators (XX.EST where XX in {GE, RQ, RL, CC, VA, PV})

All accessible via the same pattern:
    https://api.worldbank.org/v2/country/all/indicator/{code}?format=json&date=YYYY:YYYY

No API key. No auth. Generous rate limits. Paginated JSON.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from ..catalog import Indicator
from .base import DataPoint, FetchError

logger = logging.getLogger(__name__)

WB_BASE = "https://api.worldbank.org/v2"
PER_PAGE = 2000  # WB caps at ~32,500 results; 2000/page keeps responses small

# Aggregate rows (region/income group) leak into "country/all" responses.
# We filter them out by checking that country.id is a real ISO-3 and
# region.value != "Aggregates".
_AGGREGATE_REGION = "Aggregates"


async def fetch_series(
    client: httpx.AsyncClient, code: str, start_year: int, end_year: int
) -> list[dict[str, Any]]:
    """Fetch all pages of a single WB indicator series."""
    url = f"{WB_BASE}/country/all/indicator/{code}"
    params = {
        "format": "json",
        "date": f"{start_year}:{end_year}",
        "per_page": PER_PAGE,
        "page": 1,
    }

    rows: list[dict[str, Any]] = []
    while True:
        resp = await client.get(url, params=params, timeout=30.0)
        if resp.status_code != 200:
            raise FetchError(f"World Bank {code} returned HTTP {resp.status_code}")

        payload = resp.json()
        if not isinstance(payload, list) or len(payload) < 2:
            # WB error responses are objects, not [meta, data] arrays
            raise FetchError(f"World Bank {code} returned unexpected payload shape")

        meta, data = payload[0], payload[1]
        if data:
            rows.extend(data)

        total_pages = meta.get("pages", 1)
        if params["page"] >= total_pages:
            break
        params["page"] += 1

    return rows


def _row_to_datapoint(row: dict[str, Any], ind: Indicator) -> DataPoint | None:
    country = row.get("country") or {}
    country_iso3 = row.get("countryiso3code") or ""
    region = (row.get("region") or {}).get("value", "")

    # Filter aggregates and rows without a proper ISO-3
    if not country_iso3 or len(country_iso3) != 3 or region == _AGGREGATE_REGION:
        return None

    try:
        year = int(row["date"])
    except (KeyError, ValueError, TypeError):
        return None

    raw_value = row.get("value")
    value: float | None
    if raw_value is None:
        value = None
    else:
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            value = None

    return DataPoint(
        indicator_key=ind.key,
        indicator_name=ind.name,
        pillar=ind.pillar.value,
        component=ind.component,
        source=ind.source,
        country_iso3=country_iso3,
        country_name=country.get("value", ""),
        year=year,
        value=value,
        unit=ind.unit,
    )


async def fetch_indicators(
    indicators: list[Indicator], start_year: int, end_year: int
) -> list[DataPoint]:
    """Fetch multiple World Bank indicators in parallel."""
    if not indicators:
        return []

    # Limit concurrency so we don't hammer WB; 6 parallel requests is polite.
    semaphore = asyncio.Semaphore(6)
    points: list[DataPoint] = []

    async with httpx.AsyncClient(headers={"Accept": "application/json"}) as client:
        async def _one(ind: Indicator) -> list[DataPoint]:
            async with semaphore:
                try:
                    rows = await fetch_series(client, ind.source_code, start_year, end_year)
                except FetchError as exc:
                    logger.warning("World Bank fetch failed for %s: %s", ind.key, exc)
                    return []
                except httpx.RequestError as exc:
                    logger.warning("World Bank request error for %s: %s", ind.key, exc)
                    return []

                out: list[DataPoint] = []
                for row in rows:
                    dp = _row_to_datapoint(row, ind)
                    if dp is not None:
                        out.append(dp)
                return out

        results = await asyncio.gather(*[_one(ind) for ind in indicators])
        for chunk in results:
            points.extend(chunk)

    return points
