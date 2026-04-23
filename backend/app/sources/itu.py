"""ITU DataHub fetcher.

ITU exposes indicator data via a JSON endpoint on datahub.itu.int. The
endpoints are public but the schema is less stable than WB's. We're careful
to fall back to an empty result rather than raise, because ITU occasionally
rotates URLs.

Indicator IDs used here:
    11624 - Individuals using the Internet (%)
    19303 - Active mobile-broadband subscriptions per 100 inhabitants
    i99H  - Households with Internet access at home (%)

Because the official endpoints shift, this fetcher treats a 404 or schema
miss as "source unavailable" and returns [], with a warning. The frontend
surfaces this as a per-source status so the user knows which failed.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..catalog import Indicator
from .base import DataPoint

logger = logging.getLogger(__name__)

ITU_BASE = "https://api.datahub.itu.int/data"

# Map our internal indicator keys -> ITU indicator identifiers.
# The specific IDs are the ones ITU publishes on datahub.itu.int; see
# https://datahub.itu.int/data/ for the catalog.
INDICATOR_ID_MAP: dict[str, str] = {
    "itu_households_internet": "i99H",
    "itu_mobile_broadband_subs": "19303",
}


async def _fetch_one(
    client: httpx.AsyncClient, ind: Indicator, start_year: int, end_year: int
) -> list[DataPoint]:
    itu_id = INDICATOR_ID_MAP.get(ind.key)
    if not itu_id:
        return []

    params = {
        "indicator": itu_id,
        "start": start_year,
        "end": end_year,
        "format": "json",
    }

    try:
        resp = await client.get(ITU_BASE, params=params, timeout=30.0)
    except httpx.RequestError as exc:
        logger.warning("ITU request error for %s: %s", ind.key, exc)
        return []

    if resp.status_code != 200:
        logger.warning("ITU returned HTTP %s for %s", resp.status_code, ind.key)
        return []

    try:
        payload: Any = resp.json()
    except ValueError:
        logger.warning("ITU returned non-JSON for %s", ind.key)
        return []

    # ITU's response is usually a list of records with fields
    # {entity, entity_code, year, value}. Defensive parsing:
    records = payload if isinstance(payload, list) else payload.get("data", [])

    out: list[DataPoint] = []
    for row in records:
        if not isinstance(row, dict):
            continue
        iso3 = row.get("entity_code") or row.get("iso3") or ""
        if not iso3 or len(iso3) != 3:
            continue
        try:
            year = int(row.get("year") or row.get("date"))
        except (TypeError, ValueError):
            continue
        raw = row.get("value")
        try:
            value = float(raw) if raw is not None else None
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
                country_name=row.get("entity") or row.get("country") or "",
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

    out: list[DataPoint] = []
    async with httpx.AsyncClient() as client:
        for ind in indicators:
            out.extend(await _fetch_one(client, ind, start_year, end_year))
    return out
