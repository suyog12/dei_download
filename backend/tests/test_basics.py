"""Basic tests for the DEI downloader.

Offline tests validate catalog shape and workbook construction. One live test
hits World Bank with a short query to confirm end-to-end. Skip the live one
with: pytest -m 'not live'.
"""

from __future__ import annotations

import asyncio

import pytest

from app.catalog import CATALOG, Availability, Pillar, indicators_for
from app.orchestrator import build_workbook, fetch, FetchResult
from app.sources.base import DataPoint


def test_catalog_has_all_pillars():
    pillars_in_catalog = {ind.pillar for ind in CATALOG}
    assert pillars_in_catalog == set(Pillar)


def test_catalog_keys_are_unique():
    keys = [ind.key for ind in CATALOG]
    assert len(keys) == len(set(keys)), "Duplicate indicator keys in catalog"


def test_api_indicators_have_known_source():
    known_sources = {
        "World Bank",
        "World Bank Global Findex",
        "World Bank WGI",
        "World Bank / WIPO",
        "World Bank / UNESCO",
        "Our World in Data",
        "IMF",
    }
    for ind in CATALOG:
        if ind.availability == Availability.API:
            assert ind.source in known_sources, (
                f"{ind.key} has availability=api but no dispatch "
                f"is registered for source {ind.source!r}"
            )


def test_indicators_for_filters_by_pillar_and_availability():
    supply_api = indicators_for({Pillar.SUPPLY}, availability={Availability.API})
    assert all(i.pillar == Pillar.SUPPLY for i in supply_api)
    assert all(i.availability == Availability.API for i in supply_api)
    assert len(supply_api) > 0


def test_build_workbook_empty_is_valid():
    result = FetchResult(points=[], statuses=[])
    xlsx = build_workbook(result, {Pillar.SUPPLY}, 2020, 2025)
    assert xlsx[:2] == b"PK", "xlsx files start with the ZIP magic bytes PK"
    assert len(xlsx) > 1000


def test_build_workbook_with_points():
    points = [
        DataPoint(
            indicator_key="individuals_using_internet",
            indicator_name="Individuals using the Internet (% of population)",
            pillar=Pillar.SUPPLY.value,
            component="Access Infrastructure",
            source="World Bank",
            country_iso3="USA",
            country_name="United States",
            year=2023,
            value=91.7,
            unit="%",
        ),
    ]
    result = FetchResult(points=points, statuses=[])
    xlsx = build_workbook(result, {Pillar.SUPPLY}, 2020, 2025)
    assert xlsx[:2] == b"PK"


def test_countries_list_shape():
    """The 125 DEI economies must all have valid ISO-3 codes and a region."""
    from app.countries import DEI_COUNTRIES

    assert len(DEI_COUNTRIES) == 125, f"Expected 125, got {len(DEI_COUNTRIES)}"
    for c in DEI_COUNTRIES:
        assert len(c.iso3) == 3, f"{c.name} has bad ISO-3: {c.iso3!r}"
        assert c.iso3.isupper(), f"{c.name} ISO-3 should be uppercase: {c.iso3!r}"
        assert c.region in {
            "Asia Pacific",
            "Europe & Central Asia",
            "Latin America & Caribbean",
            "Middle East & Africa",
            "North America",
        }, f"{c.name} has unknown region: {c.region!r}"
    # No duplicate ISO-3s
    iso3s = [c.iso3 for c in DEI_COUNTRIES]
    assert len(iso3s) == len(set(iso3s)), "Duplicate ISO-3 in country list"


def test_countries_endpoint_returns_all():
    """/api/countries should return 125 countries grouped by region."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/countries")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 125
    assert len(data["countries"]) == 125
    # Sanity: North America should have exactly 2 (US, Canada)
    assert len(data["by_region"]["North America"]) == 2


def test_download_request_accepts_filters():
    """Pydantic validation must accept the new optional filters."""
    from app.main import DownloadRequest

    # No filters (backward compatible)
    r = DownloadRequest(pillars=["supply"], start_year=2020, end_year=2025)
    assert r.country_set() is None
    assert r.indicator_key_set() is None

    # With filters
    r = DownloadRequest(
        pillars=["supply", "demand"],
        start_year=2022,
        end_year=2024,
        countries=["USA", "vnm", "  ind  "],  # mixed case and whitespace
        indicator_keys=["individuals_using_internet"],
    )
    # Validation should normalize to uppercase and strip whitespace
    assert r.country_set() == {"USA", "VNM", "IND"}
    assert r.indicator_key_set() == {"individuals_using_internet"}

    # Empty filter lists normalize to None (treat as "no filter")
    r = DownloadRequest(
        pillars=["supply"], start_year=2020, end_year=2025, countries=[]
    )
    assert r.country_set() is None


def test_orchestrator_applies_country_filter():
    """Simulate fetched points and confirm country filtering works.

    We can't run a live fetch in the sandbox, but we can monkeypatch a source
    module to return canned points and verify the filter drops the rest.
    """
    import asyncio
    from app.orchestrator import fetch
    from app.sources import worldbank

    canned_points = [
        DataPoint(
            indicator_key="individuals_using_internet",
            indicator_name="x",
            pillar=Pillar.SUPPLY.value,
            component="Access Infrastructure",
            source="World Bank",
            country_iso3=iso,
            country_name=iso,
            year=2023,
            value=42.0,
            unit="%",
        )
        for iso in ["USA", "VNM", "IND", "DEU"]
    ]

    async def fake_fetch_indicators(indicators, start, end):
        return canned_points

    original = worldbank.fetch_indicators
    worldbank.fetch_indicators = fake_fetch_indicators  # type: ignore[assignment]
    try:
        result = asyncio.run(
            fetch({Pillar.SUPPLY}, 2023, 2023, countries={"USA", "VNM"})
        )
    finally:
        worldbank.fetch_indicators = original  # type: ignore[assignment]

    got_countries = {p.country_iso3 for p in result.points}
    assert got_countries == {"USA", "VNM"}, f"Filter leaked: {got_countries}"


def test_is_available_for_range_basic():
    """Regular indicator: overlap returns True, no overlap returns False."""
    from app.catalog import Indicator, Pillar, Availability, is_available_for_range

    ind = Indicator(
        key="test",
        name="test",
        pillar=Pillar.SUPPLY,
        component="x",
        source="x",
        source_code="x",
        availability=Availability.API,
        earliest_year=2015,
        latest_year=2023,
        publication_lag_years=1,
    )
    # Range fully inside coverage
    assert is_available_for_range(ind, 2018, 2022) is True
    # Range fully before coverage
    assert is_available_for_range(ind, 2010, 2014) is False
    # Range fully after coverage (GSMA 2023 only, user picks 2024-2025)
    assert is_available_for_range(ind, 2024, 2025) is False
    # Range overlaps the start
    assert is_available_for_range(ind, 2010, 2016) is True
    # Range overlaps the end
    assert is_available_for_range(ind, 2022, 2030) is True


def test_is_available_for_range_sparse():
    """Sparse indicators (Findex) are ALWAYS available regardless of range."""
    from app.catalog import Indicator, Pillar, Availability, is_available_for_range

    findex_like = Indicator(
        key="test",
        name="test",
        pillar=Pillar.DEMAND,
        component="x",
        source="x",
        source_code="x",
        availability=Availability.API,
        earliest_year=2011,
        latest_year=2024,
        sparse=True,
    )
    # Even for a year far outside any known wave
    assert is_available_for_range(findex_like, 2019, 2019) is True
    # Even in the far future
    assert is_available_for_range(findex_like, 2030, 2030) is True


def test_catalog_response_exposes_coverage_fields():
    """/api/catalog must include earliest_year, latest_year, publication_lag_years, sparse."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/catalog")
    assert resp.status_code == 200
    data = resp.json()
    any_indicator = data["pillars"][0]["indicators"][0]
    for field in ("earliest_year", "latest_year", "publication_lag_years", "sparse"):
        assert field in any_indicator, f"Missing field: {field}"


def test_aei_preview_endpoint_exists():
    """/api/aei/preview should return a consistent shape even when HF is unreachable."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/aei/preview")
    # 200 always — we return an "unavailable" shape rather than 5xx when the
    # CSV can't be fetched (e.g. in this sandbox with blocked egress).
    assert resp.status_code == 200
    data = resp.json()
    assert "available" in data
    # Whether available or not, the shape should include these:
    assert isinstance(data.get("variables", []), list)
    assert isinstance(data.get("country_count", 0), int)


def test_worldbank_parses_real_response_shape():
    """Verify the WB row parser against a realistic payload.

    The payload below matches the exact JSON shape api.worldbank.org returns
    for IT.NET.USER.ZS. This test catches schema drift without needing the
    network.
    """
    from app.catalog import Indicator
    from app.sources.worldbank import _row_to_datapoint

    ind = Indicator(
        key="individuals_using_internet",
        name="Individuals using the Internet (% of population)",
        pillar=Pillar.SUPPLY,
        component="Access Infrastructure",
        source="World Bank",
        source_code="IT.NET.USER.ZS",
        availability=Availability.API,
        unit="%",
    )

    # Real country row
    usa_row = {
        "indicator": {"id": "IT.NET.USER.ZS", "value": "Individuals using the Internet"},
        "country": {"id": "US", "value": "United States"},
        "countryiso3code": "USA",
        "date": "2022",
        "value": 91.75,
        "unit": "",
        "obs_status": "",
        "decimal": 1,
    }
    dp = _row_to_datapoint(usa_row, ind)
    assert dp is not None
    assert dp.country_iso3 == "USA"
    assert dp.year == 2022
    assert dp.value == 91.75

    # Aggregate row (should be filtered out)
    aggregate_row = {
        "indicator": {"id": "IT.NET.USER.ZS", "value": "..."},
        "country": {"id": "1W", "value": "World"},
        "countryiso3code": "WLD",
        "date": "2022",
        "value": 66.5,
        "region": {"id": "NA", "value": "Aggregates"},
    }
    assert _row_to_datapoint(aggregate_row, ind) is None

    # Null-value row (country didn't report that year)
    null_row = {
        "indicator": {"id": "IT.NET.USER.ZS", "value": "..."},
        "country": {"id": "ER", "value": "Eritrea"},
        "countryiso3code": "ERI",
        "date": "2022",
        "value": None,
    }
    dp = _row_to_datapoint(null_row, ind)
    assert dp is not None
    assert dp.value is None
    assert dp.country_iso3 == "ERI"


@pytest.mark.live
def test_worldbank_live_single_series():
    """Live test: fetch a small slice of WB data.

    Run with: pytest -m live. Requires network access to api.worldbank.org.
    """
    from app.sources import worldbank
    from app.catalog import Indicator

    ind = Indicator(
        key="test_internet",
        name="Test - Internet users",
        pillar=Pillar.SUPPLY,
        component="Access Infrastructure",
        source="World Bank",
        source_code="IT.NET.USER.ZS",
        availability=Availability.API,
        unit="%",
    )

    points = asyncio.run(worldbank.fetch_indicators([ind], 2022, 2023))
    assert len(points) > 0, "World Bank returned no rows; network or schema issue"
    numeric = [p for p in points if p.value is not None and len(p.country_iso3) == 3]
    assert len(numeric) > 10
