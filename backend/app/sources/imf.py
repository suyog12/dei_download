"""IMF DataMapper API fetcher.

Endpoint pattern:
    GET https://www.imf.org/external/datamapper/api/v1/{indicator_id}
    [Accept: application/json]
    [User-Agent: required for non-browser clients]

Returns:
    {
      "values": {
        "<indicator_id>": {
          "USA": {"2020": 63531, "2021": 70219, ...},
          "VNM": {"2020": 3556, ...},
          ...                              # every country IMF tracks
        }
      }
    }

Design choices:
  - We fetch the full global response for each indicator (no country path
    segment). This keeps URL length short (~65 chars) and lets us reuse the
    response for any country selection.
  - The IMF DataMapper responds differently to browsers vs scripts. Without
    a custom User-Agent the endpoint returns 403. We always send one.
  - Errors are surfaced with HTTP status codes in log messages so that when
    a source fails, the operator can distinguish between "network error",
    "403 forbidden", and "indicator code invalid" (typically 404).

Catalog convention: `source_code` is the IMF DataMapper indicator id
(e.g., "NGDP_RPCH" for real GDP growth, "PPPPC" for GDP per capita PPP).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from ..catalog import Indicator
from ..countries import DEI_COUNTRIES
from .base import DataPoint

logger = logging.getLogger(__name__)

IMF_BASE = "https://www.imf.org/external/datamapper/api/v1"
# A descriptive User-Agent is REQUIRED; default httpx UA returns 403.
UA = "DEI-Downloader/1.0 (+research; https://github.com/suyogpokhrel)"


async def _fetch_one(
    client: httpx.AsyncClient, ind: Indicator, start_year: int, end_year: int
) -> list[DataPoint]:
    url = f"{IMF_BASE}/{ind.source_code}"
    headers = {"Accept": "application/json", "User-Agent": UA}

    try:
        resp = await client.get(url, headers=headers, timeout=45.0)
    except httpx.RequestError as exc:
        logger.warning("IMF request error for %s at %s: %s", ind.key, url, exc)
        return []

    if resp.status_code != 200:
        # Truncate body in the log so we don't dump an HTML error page
        body_preview = resp.text[:200].replace("\n", " ")
        logger.warning(
            "IMF %s returned HTTP %s at %s: %s",
            ind.key,
            resp.status_code,
            url,
            body_preview,
        )
        return []

    try:
        payload: dict[str, Any] = resp.json()
    except ValueError:
        logger.warning("IMF %s returned non-JSON body (len=%s)", ind.key, len(resp.text))
        return []

    values = (payload.get("values") or {}).get(ind.source_code) or {}
    if not isinstance(values, dict):
        logger.warning(
            "IMF %s has unexpected values shape: %s",
            ind.key,
            type(values).__name__,
        )
        return []

    # Build a name lookup from the DEI catalog so rows get human country names
    name_by_iso3 = {c.iso3: c.name for c in DEI_COUNTRIES}

    out: list[DataPoint] = []
    for iso3, year_map in values.items():
        iso3 = (iso3 or "").upper()
        if len(iso3) != 3 or not isinstance(year_map, dict):
            continue
        for year_str, raw in year_map.items():
            try:
                year = int(year_str)
            except (TypeError, ValueError):
                continue
            if year < start_year or year > end_year:
                continue
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
                    country_name=name_by_iso3.get(iso3, iso3),
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

    semaphore = asyncio.Semaphore(3)
    out: list[DataPoint] = []

    async with httpx.AsyncClient() as client:
        async def _bound(ind: Indicator) -> list[DataPoint]:
            async with semaphore:
                return await _fetch_one(client, ind, start_year, end_year)

        results = await asyncio.gather(*[_bound(ind) for ind in indicators])
        for chunk in results:
            out.extend(chunk)

    return out
