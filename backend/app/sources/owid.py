"""Our World in Data Chart API fetcher.

OWID exposes every chart as a plain CSV at:
    https://ourworldindata.org/grapher/{slug}.csv?v=1&csvType=full

No auth, no API key, CC-BY licensed. The CSV columns are stable:
    Entity,Code,Year,<variable_name>

where Entity is the country name, Code is the ISO-3 (or OWID-specific code
like OWID_WRL for aggregates), Year is YYYY, and the last column(s) are the
indicator values.

A "User-Agent" header is required per OWID's ToS to avoid being rate-limited.

This module is especially valuable for moving indicators that are otherwise
manual-only: OWID re-hosts Freedom House, V-Dem, and Polity scores as CSVs,
so we can fetch them programmatically through OWID even though those sources
don't offer APIs themselves.
"""

from __future__ import annotations

import asyncio
import csv
import io
import logging

import httpx

from ..catalog import Indicator
from .base import DataPoint

logger = logging.getLogger(__name__)

OWID_BASE = "https://ourworldindata.org/grapher"
UA = "DEI-Downloader/1.0 (+research tool)"


async def _fetch_chart_csv(
    client: httpx.AsyncClient, slug: str
) -> str | None:
    url = f"{OWID_BASE}/{slug}.csv"
    params = {"v": "1", "csvType": "full", "useColumnShortNames": "true"}
    try:
        resp = await client.get(url, params=params, timeout=30.0, follow_redirects=True)
    except httpx.RequestError as exc:
        logger.warning("OWID request error for %s: %s", slug, exc)
        return None
    if resp.status_code != 200:
        logger.warning("OWID %s returned HTTP %s", slug, resp.status_code)
        return None
    # Empty or HTML fallback (404 page) is a common failure mode
    if not resp.text.strip() or resp.text.lstrip().startswith("<"):
        logger.warning("OWID %s returned non-CSV body", slug)
        return None
    return resp.text


def _parse_csv(text: str, ind: Indicator, start_year: int, end_year: int) -> list[DataPoint]:
    """Parse OWID CSV into DataPoints.

    The last column is usually the value. If the CSV has multiple value columns
    (some OWID charts bundle related series), we pick the one matching the
    source_code (short name) if we can find it, else we fall back to the last
    numeric-typed column.
    """
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = reader.fieldnames or []
    if not fieldnames:
        return []

    # Standard metadata columns
    fixed = {"Entity", "Code", "Year"}
    value_columns = [f for f in fieldnames if f not in fixed]
    if not value_columns:
        return []

    # Prefer a column whose short name matches our source_code
    value_col = next(
        (c for c in value_columns if c == ind.source_code),
        value_columns[-1],
    )

    out: list[DataPoint] = []
    for row in reader:
        iso3 = (row.get("Code") or "").strip().upper()
        # OWID aggregates have codes like OWID_WRL; skip anything not a 3-letter ISO
        if len(iso3) != 3:
            continue
        try:
            year = int(row.get("Year") or "")
        except (TypeError, ValueError):
            continue
        if year < start_year or year > end_year:
            continue

        raw = (row.get(value_col) or "").strip()
        try:
            value = float(raw) if raw else None
        except ValueError:
            value = None

        out.append(
            DataPoint(
                indicator_key=ind.key,
                indicator_name=ind.name,
                pillar=ind.pillar.value,
                component=ind.component,
                source=ind.source,
                country_iso3=iso3,
                country_name=row.get("Entity") or "",
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

    semaphore = asyncio.Semaphore(4)
    out: list[DataPoint] = []

    async with httpx.AsyncClient(headers={"User-Agent": UA}) as client:
        async def _one(ind: Indicator) -> list[DataPoint]:
            async with semaphore:
                # The source_code for OWID indicators is the grapher slug
                # (e.g., "political-rights-rating-fh"), not a series ID.
                # We use the key as the slug convention: catalog entries for
                # OWID indicators set source_code to the slug.
                text = await _fetch_chart_csv(client, ind.source_code)
                if text is None:
                    return []
                return _parse_csv(text, ind, start_year, end_year)

        results = await asyncio.gather(*[_one(ind) for ind in indicators])
        for chunk in results:
            out.extend(chunk)

    return out
