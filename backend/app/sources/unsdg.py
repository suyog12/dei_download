"""UN SDG Indicators API fetcher.

Official endpoint at https://unstats.un.org/SDGAPI/v1/
This is a REST API (not SDMX-REST), with these relevant endpoints:

    GET /v1/sdg/Series/Data?seriesCode=XX&geoAreaCode=CODE&timePeriodStart=YYYY&timePeriodEnd=YYYY

Countries in the SDG API are identified by UN M49 numeric codes (e.g., USA=840,
Vietnam=704), not ISO-3. We maintain a small mapping from our ISO-3 catalog
to M49 codes for the DEI economies.

Catalog convention: `source_code` for UN SDG indicators is the Series Code
(e.g., "IT_USE_ii99" for mobile broadband subscriptions).
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

UNSDG_BASE = "https://unstats.un.org/SDGAPI/v1/sdg"
UA = "DEI-Downloader/1.0"

# ISO-3 to UN M49 numeric code for the 125 DEI economies.
# These numeric codes are what the SDG API expects for geoAreaCode.
ISO3_TO_M49: dict[str, str] = {
    "AFG": "4", "ALB": "8", "DZA": "12", "AGO": "24", "ARG": "32",
    "ARM": "51", "AUS": "36", "AUT": "40", "AZE": "31", "BHR": "48",
    "BGD": "50", "BLR": "112", "BEL": "56", "BEN": "204", "BOL": "68",
    "BIH": "70", "BWA": "72", "BRA": "76", "BGR": "100", "KHM": "116",
    "CMR": "120", "CAN": "124", "CHL": "152", "CHN": "156", "COL": "170",
    "CRI": "188", "CIV": "384", "HRV": "191", "CYP": "196", "CZE": "203",
    "DNK": "208", "DOM": "214", "ECU": "218", "EGY": "818", "SLV": "222",
    "EST": "233", "ETH": "231", "FIN": "246", "FRA": "250", "GEO": "268",
    "DEU": "276", "GHA": "288", "GRC": "300", "GTM": "320", "HND": "340",
    "HKG": "344", "HUN": "348", "ISL": "352", "IND": "356", "IDN": "360",
    "IRN": "364", "IRQ": "368", "IRL": "372", "ISR": "376", "ITA": "380",
    "JAM": "388", "JPN": "392", "JOR": "400", "KAZ": "398", "KEN": "404",
    "KOR": "410", "KWT": "414", "KGZ": "417", "LAO": "418", "LVA": "428",
    "LBN": "422", "LTU": "440", "LUX": "442", "MDG": "450", "MWI": "454",
    "MYS": "458", "MLI": "466", "MLT": "470", "MUS": "480", "MEX": "484",
    "MDA": "498", "MNG": "496", "MNE": "499", "MAR": "504", "NAM": "516",
    "NPL": "524", "NLD": "528", "NZL": "554", "NIC": "558", "NGA": "566",
    "MKD": "807", "NOR": "578", "OMN": "512", "PAK": "586", "PAN": "591",
    "PRY": "600", "PER": "604", "PHL": "608", "POL": "616", "PRT": "620",
    "QAT": "634", "ROU": "642", "RUS": "643", "RWA": "646", "SAU": "682",
    "SEN": "686", "SRB": "688", "SGP": "702", "SVK": "703", "SVN": "705",
    "ZAF": "710", "ESP": "724", "LKA": "144", "SWE": "752", "CHE": "756",
    "TWN": "158", "TZA": "834", "THA": "764", "TUN": "788", "TUR": "792",
    "UGA": "800", "UKR": "804", "ARE": "784", "GBR": "826", "USA": "840",
    "URY": "858", "UZB": "860", "VEN": "862", "VNM": "704", "ZMB": "894",
    "ZWE": "716",
}

# Reverse lookup for parsing responses back to ISO-3
M49_TO_ISO3: dict[str, str] = {v: k for k, v in ISO3_TO_M49.items()}


async def _fetch_one(
    client: httpx.AsyncClient, ind: Indicator, start_year: int, end_year: int
) -> list[DataPoint]:
    series_code = ind.source_code
    # Fetch all DEI countries in one call using comma-separated M49 codes.
    # The SDG API accepts multiple geoAreaCode params OR a comma-separated list;
    # to keep URL length reasonable we batch in groups of 40.
    m49_codes = [ISO3_TO_M49[c.iso3] for c in DEI_COUNTRIES if c.iso3 in ISO3_TO_M49]
    batches = [m49_codes[i : i + 40] for i in range(0, len(m49_codes), 40)]

    out: list[DataPoint] = []
    for batch in batches:
        params: list[tuple[str, str]] = [
            ("seriesCode", series_code),
            ("timePeriodStart", str(start_year)),
            ("timePeriodEnd", str(end_year)),
            ("pageSize", "5000"),
        ]
        for code in batch:
            params.append(("geoAreaCode", code))

        try:
            resp = await client.get(
                f"{UNSDG_BASE}/Series/Data",
                params=params,
                headers={"Accept": "application/json", "User-Agent": UA},
                timeout=45.0,
            )
        except httpx.RequestError as exc:
            logger.warning("UN SDG request error for %s: %s", ind.key, exc)
            continue

        if resp.status_code != 200:
            logger.warning("UN SDG %s returned HTTP %s", ind.key, resp.status_code)
            continue

        try:
            payload = resp.json()
        except ValueError:
            logger.warning("UN SDG %s returned non-JSON", ind.key)
            continue

        rows = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            continue

        for row in rows:
            m49 = str(row.get("geoAreaCode") or "")
            iso3 = M49_TO_ISO3.get(m49)
            if not iso3:
                continue
            try:
                year = int(row.get("timePeriodStart") or row.get("TimePeriod") or "")
            except (TypeError, ValueError):
                continue
            raw = row.get("value")
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
                    country_name=row.get("geoAreaName") or "",
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
