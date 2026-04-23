"""OECD SDMX-REST fetcher.

Endpoint pattern:
    https://sdmx.oecd.org/public/rest/data/{agency},{dataflow},{version}/{key}
    ?startPeriod=YYYY&endPeriod=YYYY&dimensionAtObservation=AllDimensions&format=jsondata

The `key` is a dot-separated dimension filter. For most DEI-relevant series
we leave the country dimension empty ("..") to fetch all countries.

Response shape (SDMX-JSON 1.0):
    {
      "header": {...},
      "dataSets": [{
        "observations": {
          "0:0:0:0": [value, ...],       # index tuple -> [value, flags...]
          ...
        }
      }],
      "structure": {
        "dimensions": {
          "observation": [
            {"id": "REF_AREA", "values": [{"id": "AUS", "name": "Australia"}, ...]},
            {"id": "TIME_PERIOD", "values": [{"id": "2020"}, ...]},
            ...
          ]
        }
      }
    }

OECD coverage is limited to ~38 OECD members plus a handful of partner
economies, so many DEI countries will have no data. That's fine — we'll
just have fewer rows for those countries.

Catalog convention: `source_code` for OECD indicators is a compact string
of the form "{agency}|{dataflow}|{version}|{key_filter}". Example:
    "OECD.STI.PIE|DSD_PIE@DF_R_D_EXP|1.0|.A.USD_PPP.R_D_TOTAL.."
The fetch code parses that into a URL.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from ..catalog import Indicator
from .base import DataPoint

logger = logging.getLogger(__name__)

OECD_BASE = "https://sdmx.oecd.org/public/rest/data"
UA = "DEI-Downloader/1.0"


def _parse_source_code(code: str) -> tuple[str, str] | None:
    """Split catalog source_code into (path_segment, key_filter)."""
    parts = code.split("|")
    if len(parts) != 4:
        logger.warning("OECD source_code %r does not have 4 |-separated parts", code)
        return None
    agency, dataflow, version, key = parts
    path = f"{agency},{dataflow},{version}/{key}"
    return path, key


async def _fetch_one(
    client: httpx.AsyncClient, ind: Indicator, start_year: int, end_year: int
) -> list[DataPoint]:
    parsed = _parse_source_code(ind.source_code)
    if parsed is None:
        return []
    path, _key = parsed

    url = f"{OECD_BASE}/{path}"
    params = {
        "startPeriod": str(start_year),
        "endPeriod": str(end_year),
        "dimensionAtObservation": "AllDimensions",
        "format": "jsondata",
    }
    headers = {"Accept": "application/vnd.sdmx.data+json; version=1.0", "User-Agent": UA}

    try:
        resp = await client.get(url, params=params, headers=headers, timeout=45.0)
    except httpx.RequestError as exc:
        logger.warning("OECD request error for %s: %s", ind.key, exc)
        return []

    if resp.status_code == 404:
        # OECD returns 404 when a query matches no data, not an error
        return []
    if resp.status_code != 200:
        logger.warning("OECD %s returned HTTP %s", ind.key, resp.status_code)
        return []

    try:
        payload: dict[str, Any] = resp.json()
    except ValueError:
        logger.warning("OECD %s returned non-JSON", ind.key)
        return []

    return _parse_sdmx_json(payload, ind)


def _parse_sdmx_json(payload: dict[str, Any], ind: Indicator) -> list[DataPoint]:
    """Parse SDMX-JSON 1.0 response into DataPoints.

    The observation keys are colon-separated tuples of dimension indices.
    We need to find the REF_AREA and TIME_PERIOD dimension positions, then
    map each tuple to a (country, year, value).
    """
    data_sets = payload.get("dataSets") or []
    if not data_sets:
        return []
    observations = data_sets[0].get("observations") or {}
    if not observations:
        return []

    structure = payload.get("structure") or {}
    dims = (structure.get("dimensions") or {}).get("observation") or []
    if not dims:
        return []

    # Find positions of REF_AREA and TIME_PERIOD
    ref_area_pos = None
    time_pos = None
    area_values: list[dict[str, Any]] = []
    time_values: list[dict[str, Any]] = []
    for i, d in enumerate(dims):
        dim_id = d.get("id")
        if dim_id == "REF_AREA":
            ref_area_pos = i
            area_values = d.get("values") or []
        elif dim_id == "TIME_PERIOD":
            time_pos = i
            time_values = d.get("values") or []

    if ref_area_pos is None or time_pos is None:
        logger.warning("OECD %s: could not find REF_AREA or TIME_PERIOD dimensions", ind.key)
        return []

    out: list[DataPoint] = []
    for key, obs_array in observations.items():
        idx_parts = key.split(":")
        try:
            area_idx = int(idx_parts[ref_area_pos])
            time_idx = int(idx_parts[time_pos])
        except (IndexError, ValueError):
            continue

        if area_idx >= len(area_values) or time_idx >= len(time_values):
            continue

        area = area_values[area_idx]
        time = time_values[time_idx]
        iso3 = (area.get("id") or "").upper()
        # OECD also returns region codes (OECD, G20, EU27_2020); skip non-ISO3
        if len(iso3) != 3:
            continue

        try:
            year = int(time.get("id") or "")
        except (TypeError, ValueError):
            continue

        # obs_array is [value, status_flag, ...]; value may be None
        if not isinstance(obs_array, list) or not obs_array:
            continue
        raw = obs_array[0]
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
                country_name=area.get("name") or "",
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

    semaphore = asyncio.Semaphore(3)  # OECD has strict rate limits
    out: list[DataPoint] = []

    async with httpx.AsyncClient() as client:
        async def _bound(ind: Indicator) -> list[DataPoint]:
            async with semaphore:
                return await _fetch_one(client, ind, start_year, end_year)

        results = await asyncio.gather(*[_bound(ind) for ind in indicators])
        for chunk in results:
            out.extend(chunk)

    return out
