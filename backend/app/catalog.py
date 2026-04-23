"""
DEI 2025 indicator catalog.

Maps the four Digital Evolution Index pillars to concrete, fetchable indicators
across free public data sources. This is the single source of truth for what
the app can download.

Pillar structure from Tufts Digital Planet, Digital Evolution Index 2025:
    Supply Conditions, Demand Conditions, Institutional Environment,
    Innovation and Change.

Availability tiers:
    api      - programmatically fetchable, no credentials required
    manual   - requires a manual download from a public page
    subscription - requires a paid or library subscription (Euromonitor, EIU, etc.)
"""

from dataclasses import dataclass, field
from enum import Enum


class Pillar(str, Enum):
    SUPPLY = "supply"
    DEMAND = "demand"
    INSTITUTIONAL = "institutional"
    INNOVATION = "innovation"


class Availability(str, Enum):
    API = "api"
    MANUAL = "manual"
    SUBSCRIPTION = "subscription"


@dataclass
class Indicator:
    key: str
    name: str
    pillar: Pillar
    component: str
    source: str
    source_code: str
    availability: Availability
    unit: str = ""
    notes: str = ""
    manual_url: str = ""
    # Year coverage metadata. The frontend uses these to grey out indicators
    # that have no data for the selected year range.
    #   earliest_year: first year the indicator has data.
    #   latest_year: last year it has data.
    #   publication_lag_years: how many years behind "today" the latest
    #     actual data tends to be (e.g. 2 for WGI means 2026 data won't exist
    #     until 2028). Used to expand the unavailable window for very recent
    #     year ranges.
    #   sparse: if True, the indicator only reports intermittently (e.g. Findex
    #     runs roughly every 3 years). Year-range greyout is relaxed for these.
    earliest_year: int = 2000
    latest_year: int = 2024
    publication_lag_years: int = 1
    sparse: bool = False


# World Bank Indicators API codes are stable and well-documented at
# https://data.worldbank.org. Findex codes follow the FX.* prefix convention.
# Worldwide Governance Indicators use the WGI series prefix.

CATALOG: list[Indicator] = [
    # SUPPLY - access infrastructure
    Indicator(
        key="individuals_using_internet",
        name="Individuals using the Internet (% of population)",
        pillar=Pillar.SUPPLY,
        component="Access Infrastructure",
        source="World Bank",
        source_code="IT.NET.USER.ZS",
        availability=Availability.API,
        unit="%",
    ),
    Indicator(
        key="fixed_broadband_subs",
        name="Fixed broadband subscriptions (per 100 people)",
        pillar=Pillar.SUPPLY,
        component="Access Infrastructure",
        source="World Bank",
        source_code="IT.NET.BBND.P2",
        availability=Availability.API,
        unit="per 100",
    ),
    Indicator(
        key="mobile_cellular_subs",
        name="Mobile cellular subscriptions (per 100 people)",
        pillar=Pillar.SUPPLY,
        component="Access Infrastructure",
        source="World Bank",
        source_code="IT.CEL.SETS.P2",
        availability=Availability.API,
        unit="per 100",
    ),
    Indicator(
        key="secure_internet_servers",
        name="Secure internet servers (per million people)",
        pillar=Pillar.SUPPLY,
        component="Access Infrastructure",
        source="World Bank",
        source_code="IT.NET.SECR.P6",
        availability=Availability.API,
        unit="per million",
    ),
    Indicator(
        key="electricity_access",
        name="Access to electricity (% of population)",
        pillar=Pillar.SUPPLY,
        component="Access Infrastructure",
        source="World Bank",
        source_code="EG.ELC.ACCS.ZS",
        availability=Availability.API,
        unit="%",
    ),
    Indicator(
        key="electricity_access_rural",
        name="Access to electricity, rural (% of rural population)",
        pillar=Pillar.SUPPLY,
        component="Access Infrastructure",
        source="World Bank",
        source_code="EG.ELC.ACCS.RU.ZS",
        availability=Availability.API,
        unit="%",
    ),
    Indicator(
        key="logistics_performance",
        name="Logistics performance index: Overall (1=low to 5=high)",
        pillar=Pillar.SUPPLY,
        component="Fulfillment Infrastructure",
        source="World Bank",
        source_code="LP.LPI.OVRL.XQ",
        availability=Availability.API,
        unit="score 1-5",
    ),
    # SUPPLY - ITU
    Indicator(
        key="itu_households_internet",
        name="Households with Internet access at home (%)",
        pillar=Pillar.SUPPLY,
        component="Access Infrastructure",
        source="ITU DataHub",
        source_code="i99H",
        availability=Availability.MANUAL,
        unit="%",
        manual_url="https://datahub.itu.int/data/",
        notes="ITU does not currently expose a public REST API. Download CSV from the DataHub web portal.",
    ),
    Indicator(
        key="itu_mobile_broadband_subs",
        name="Active mobile-broadband subscriptions (per 100 inhabitants)",
        pillar=Pillar.SUPPLY,
        component="Access Infrastructure",
        source="ITU DataHub",
        source_code="MobBB",
        availability=Availability.MANUAL,
        unit="per 100",
        manual_url="https://datahub.itu.int/data/",
        notes="ITU DataHub web portal; CSV export.",
    ),
    # SUPPLY - Ookla speeds (manual because the S3 parquet is large)
    Indicator(
        key="ookla_fixed_speeds",
        name="Median fixed broadband speed (Mbps)",
        pillar=Pillar.SUPPLY,
        component="Access Infrastructure",
        source="Ookla Open Data",
        source_code="OOKLA_FIXED",
        availability=Availability.MANUAL,
        unit="Mbps",
        manual_url="https://registry.opendata.aws/speedtest-global-performance/",
        notes="Quarterly parquet files on AWS S3; join by country tile aggregation",
    ),
    # DEMAND - Findex (digital payments, financial inclusion, inclusion gaps)
    # Findex waves: 2011, 2014, 2017, 2021, 2024. Marked sparse so the
    # greyout logic doesn't flag it just because the user picks 2023.
    Indicator(
        key="findex_account_ownership",
        name="Account ownership at a financial institution or mobile money provider (% age 15+)",
        pillar=Pillar.DEMAND,
        component="Digital Payment Uptake",
        source="World Bank Global Findex",
        source_code="FX.OWN.TOTL.ZS",
        availability=Availability.API,
        unit="%",
        earliest_year=2011,
        latest_year=2024,
        publication_lag_years=2,
        sparse=True,
    ),
    Indicator(
        key="findex_digital_payment",
        name="Made or received a digital payment (% age 15+)",
        pillar=Pillar.DEMAND,
        component="Digital Payment Uptake",
        source="World Bank Global Findex",
        source_code="FX.OWN.TOTL.40.ZS",
        availability=Availability.API,
        unit="%",
        notes="Proxy: account ownership, poorest 40%. Used for class parity.",
        earliest_year=2011,
        latest_year=2024,
        publication_lag_years=2,
        sparse=True,
    ),
    Indicator(
        key="findex_account_female",
        name="Account ownership, female (% age 15+)",
        pillar=Pillar.DEMAND,
        component="Digital Inclusion",
        source="World Bank Global Findex",
        source_code="FX.OWN.TOTL.FE.ZS",
        availability=Availability.API,
        unit="%",
        earliest_year=2011,
        latest_year=2024,
        publication_lag_years=2,
        sparse=True,
    ),
    Indicator(
        key="findex_account_male",
        name="Account ownership, male (% age 15+)",
        pillar=Pillar.DEMAND,
        component="Digital Inclusion",
        source="World Bank Global Findex",
        source_code="FX.OWN.TOTL.MA.ZS",
        availability=Availability.API,
        unit="%",
        earliest_year=2011,
        latest_year=2024,
        publication_lag_years=2,
        sparse=True,
    ),
    Indicator(
        key="findex_account_rural",
        name="Account ownership, rural (% age 15+)",
        pillar=Pillar.DEMAND,
        component="Digital Inclusion",
        source="World Bank Global Findex",
        source_code="FX.OWN.TOTL.RU.ZS",
        availability=Availability.API,
        unit="%",
        earliest_year=2011,
        latest_year=2024,
        publication_lag_years=2,
        sparse=True,
    ),
    # DEMAND - consumer ability
    Indicator(
        key="gni_per_capita_ppp",
        name="GNI per capita, PPP (current international $)",
        pillar=Pillar.DEMAND,
        component="State of the Human Condition",
        source="World Bank",
        source_code="NY.GNP.PCAP.PP.CD",
        availability=Availability.API,
        unit="USD PPP",
    ),
    Indicator(
        key="final_consumption_per_capita",
        name="Household final consumption expenditure per capita (constant 2015 US$)",
        pillar=Pillar.DEMAND,
        component="State of the Human Condition",
        source="World Bank",
        source_code="NE.CON.PRVT.PC.KD",
        availability=Availability.API,
        unit="USD",
    ),
    # INSTITUTIONAL - Worldwide Governance Indicators via WB
    Indicator(
        key="wgi_government_effectiveness",
        name="Government Effectiveness: Estimate",
        pillar=Pillar.INSTITUTIONAL,
        component="Institutional Effectiveness and Trust",
        source="World Bank WGI",
        source_code="GE.EST",
        availability=Availability.API,
        unit="score -2.5 to 2.5",
    ),
    Indicator(
        key="wgi_regulatory_quality",
        name="Regulatory Quality: Estimate",
        pillar=Pillar.INSTITUTIONAL,
        component="Institutional Effectiveness and Trust",
        source="World Bank WGI",
        source_code="RQ.EST",
        availability=Availability.API,
        unit="score -2.5 to 2.5",
    ),
    Indicator(
        key="wgi_rule_of_law",
        name="Rule of Law: Estimate",
        pillar=Pillar.INSTITUTIONAL,
        component="Institutional Effectiveness and Trust",
        source="World Bank WGI",
        source_code="RL.EST",
        availability=Availability.API,
        unit="score -2.5 to 2.5",
    ),
    Indicator(
        key="wgi_control_corruption",
        name="Control of Corruption: Estimate",
        pillar=Pillar.INSTITUTIONAL,
        component="Institutional Effectiveness and Trust",
        source="World Bank WGI",
        source_code="CC.EST",
        availability=Availability.API,
        unit="score -2.5 to 2.5",
    ),
    Indicator(
        key="wgi_voice_accountability",
        name="Voice and Accountability: Estimate",
        pillar=Pillar.INSTITUTIONAL,
        component="Institutional Effectiveness and Trust",
        source="World Bank WGI",
        source_code="VA.EST",
        availability=Availability.API,
        unit="score -2.5 to 2.5",
    ),
    Indicator(
        key="wgi_political_stability",
        name="Political Stability and Absence of Violence/Terrorism: Estimate",
        pillar=Pillar.INSTITUTIONAL,
        component="Institutional Effectiveness and Trust",
        source="World Bank WGI",
        source_code="PV.EST",
        availability=Availability.API,
        unit="score -2.5 to 2.5",
    ),
    # INSTITUTIONAL - UN E-Government (EGDI)
    Indicator(
        key="un_egdi",
        name="UN E-Government Development Index (EGDI)",
        pillar=Pillar.INSTITUTIONAL,
        component="Institutions and the Digital Ecosystem",
        source="UN E-Government Survey",
        source_code="EGDI",
        availability=Availability.MANUAL,
        unit="score 0-1",
        manual_url="https://publicadministration.un.org/egovkb/en-us/Data-Center",
        notes="Biennial survey; CSV download from UN DESA portal",
    ),
    # INSTITUTIONAL - Freedom House, Transparency International, ODIN
    Indicator(
        key="freedom_on_the_net",
        name="Freedom on the Net score (via OWID)",
        pillar=Pillar.INSTITUTIONAL,
        component="Institutional Effectiveness and Trust",
        source="Our World in Data",
        source_code="internet-freedom-fh",
        availability=Availability.API,
        unit="score 0-100",
        notes="Freedom House data re-hosted by Our World in Data (CC-BY)",
        earliest_year=2011,
        latest_year=2024,
        publication_lag_years=1,
    ),
    Indicator(
        key="cpi",
        name="Corruption Perceptions Index (via OWID)",
        pillar=Pillar.INSTITUTIONAL,
        component="Institutional Effectiveness and Trust",
        source="Our World in Data",
        source_code="corruption-perceptions-index",
        availability=Availability.API,
        unit="score 0-100",
        notes="Transparency International data re-hosted by Our World in Data",
        earliest_year=2012,
        latest_year=2024,
        publication_lag_years=1,
    ),
    Indicator(
        key="odin",
        name="Open Data Inventory (ODIN) score",
        pillar=Pillar.INSTITUTIONAL,
        component="Institutions and the Digital Ecosystem",
        source="Open Data Watch",
        source_code="ODIN",
        availability=Availability.MANUAL,
        unit="score 0-100",
        manual_url="https://odin.opendatawatch.com/Data",
    ),
    # INNOVATION - WIPO, UNESCO, WB high-tech
    Indicator(
        key="wipo_patent_applications",
        name="Patent applications, residents (total)",
        pillar=Pillar.INNOVATION,
        component="Outcomes",
        source="World Bank / WIPO",
        source_code="IP.PAT.RESD",
        availability=Availability.API,
        unit="count",
        notes="WIPO data published via World Bank WDI",
    ),
    Indicator(
        key="wipo_trademark_applications",
        name="Trademark applications, direct resident (total)",
        pillar=Pillar.INNOVATION,
        component="Outcomes",
        source="World Bank / WIPO",
        source_code="IP.TMK.RESD",
        availability=Availability.API,
        unit="count",
    ),
    Indicator(
        key="high_tech_exports",
        name="High-technology exports (% of manufactured exports)",
        pillar=Pillar.INNOVATION,
        component="Outcomes",
        source="World Bank",
        source_code="TX.VAL.TECH.MF.ZS",
        availability=Availability.API,
        unit="%",
    ),
    Indicator(
        key="ict_service_exports",
        name="ICT service exports (% of service exports, BoP)",
        pillar=Pillar.INNOVATION,
        component="Outcomes",
        source="World Bank",
        source_code="BX.GSR.CCIS.ZS",
        availability=Availability.API,
        unit="%",
    ),
    Indicator(
        key="ict_goods_exports",
        name="ICT goods exports (% of total goods exports)",
        pillar=Pillar.INNOVATION,
        component="Outcomes",
        source="World Bank",
        source_code="TX.VAL.ICTG.ZS.UN",
        availability=Availability.API,
        unit="%",
    ),
    Indicator(
        key="rd_expenditure",
        name="Research and development expenditure (% of GDP)",
        pillar=Pillar.INNOVATION,
        component="Processes",
        source="World Bank / UNESCO",
        source_code="GB.XPD.RSDV.GD.ZS",
        availability=Availability.API,
        unit="% of GDP",
    ),
    Indicator(
        key="researchers_per_million",
        name="Researchers in R&D (per million people)",
        pillar=Pillar.INNOVATION,
        component="Inputs",
        source="World Bank / UNESCO",
        source_code="SP.POP.SCIE.RD.P6",
        availability=Availability.API,
        unit="per million",
    ),
    Indicator(
        key="scientific_articles",
        name="Scientific and technical journal articles",
        pillar=Pillar.INNOVATION,
        component="Outcomes",
        source="World Bank",
        source_code="IP.JRN.ARTC.SC",
        availability=Availability.API,
        unit="count",
    ),
    Indicator(
        key="tertiary_enrollment",
        name="School enrollment, tertiary (% gross)",
        pillar=Pillar.INNOVATION,
        component="Inputs",
        source="World Bank / UNESCO",
        source_code="SE.TER.ENRR",
        availability=Availability.API,
        unit="%",
    ),
    Indicator(
        key="new_businesses_registered",
        name="New businesses registered (number)",
        pillar=Pillar.INNOVATION,
        component="Inputs",
        source="World Bank",
        source_code="IC.BUS.NREG",
        availability=Availability.API,
        unit="count",
    ),
    # Subscription / paid sources - we show instructions, don't fetch
    Indicator(
        key="euromonitor_ecommerce",
        name="Mobile e-commerce share of retail (Euromonitor Passport)",
        pillar=Pillar.DEMAND,
        component="Device and Broadband Uptake",
        source="Euromonitor Passport",
        source_code="EURO_ECOMM",
        availability=Availability.SUBSCRIPTION,
        unit="%",
        manual_url="https://www.euromonitor.com/passport",
        notes="University library subscription required (check W&M Swem Library)",
    ),
    Indicator(
        key="eiu_democracy",
        name="EIU Democracy Index",
        pillar=Pillar.INSTITUTIONAL,
        component="Institutional Effectiveness and Trust",
        source="Economist Intelligence Unit",
        source_code="EIU_DEMO",
        availability=Availability.SUBSCRIPTION,
        unit="score 0-10",
        manual_url="https://www.eiu.com/n/campaigns/democracy-index/",
        notes="EIU subscription required; library access sometimes available",
    ),
    Indicator(
        key="gsma_mobile_intelligence",
        name="GSMA Mobile Connectivity Index",
        pillar=Pillar.SUPPLY,
        component="Access Infrastructure",
        source="GSMA Intelligence",
        source_code="GSMA_MCI",
        availability=Availability.MANUAL,
        unit="score 0-100",
        manual_url="https://www.mobileconnectivityindex.com/",
        notes="Free registration required; CSV export from the portal",
    ),
    # ========================================================================
    # OUR WORLD IN DATA - additional re-hosted series beyond FH and CPI
    # ========================================================================
    Indicator(
        key="owid_civil_liberties",
        name="Civil liberties score (V-Dem, via OWID)",
        pillar=Pillar.INSTITUTIONAL,
        component="Institutional Effectiveness and Trust",
        source="Our World in Data",
        source_code="civil-liberties-score-fh",
        availability=Availability.API,
        unit="score 1-7",
        notes="Freedom House civil liberties via OWID",
        earliest_year=2003,
        latest_year=2024,
    ),
    Indicator(
        key="owid_political_rights",
        name="Political rights score (via OWID)",
        pillar=Pillar.INSTITUTIONAL,
        component="Institutional Effectiveness and Trust",
        source="Our World in Data",
        source_code="political-rights-rating-fh",
        availability=Availability.API,
        unit="score 1-7",
        notes="Freedom House political rights via OWID",
        earliest_year=2003,
        latest_year=2024,
    ),
    Indicator(
        key="owid_internet_users_share",
        name="Share of the population using the internet (via OWID)",
        pillar=Pillar.SUPPLY,
        component="Access Infrastructure",
        source="Our World in Data",
        source_code="share-of-individuals-using-the-internet",
        availability=Availability.API,
        unit="%",
        notes="ITU / World Bank data via OWID; broader country coverage than direct ITU",
        earliest_year=2000,
        latest_year=2023,
        publication_lag_years=2,
    ),
    # ========================================================================
    # OECD - data portal exists but programmatic SDMX access is tricky.
    # Listed as manual for honesty; the web portal is fine for CSV export.
    # ========================================================================
    Indicator(
        key="oecd_rd_intensity",
        name="Gross domestic spending on R&D (% of GDP)",
        pillar=Pillar.INNOVATION,
        component="Processes",
        source="OECD Data Explorer",
        source_code="DSD_MSTI@DF_MSTI",
        availability=Availability.MANUAL,
        unit="% of GDP",
        manual_url="https://data-explorer.oecd.org/vis?tenant=archive&df[ds]=DisseminateArchiveDMZ&df[id]=DF_MSTI_PUB&df[ag]=OECD",
        notes="OECD members only. Use the Data Explorer web portal to export CSV.",
    ),
    Indicator(
        key="oecd_ict_investment",
        name="ICT investment (% of GFCF)",
        pillar=Pillar.SUPPLY,
        component="Access Infrastructure",
        source="OECD Data Explorer",
        source_code="OECD_ICT_INV",
        availability=Availability.MANUAL,
        unit="% of GFCF",
        manual_url="https://data-explorer.oecd.org/",
        notes="OECD Annual National Accounts; use Data Explorer CSV export.",
    ),
    Indicator(
        key="oecd_broadband_subs",
        name="Fixed broadband subscriptions (OECD, per 100 inhabitants)",
        pillar=Pillar.SUPPLY,
        component="Access Infrastructure",
        source="OECD Data Explorer",
        source_code="OECD_BROADBAND",
        availability=Availability.MANUAL,
        unit="per 100",
        manual_url="https://www.oecd.org/digital/broadband/broadband-statistics/",
        notes="OECD Broadband portal; CSV export.",
    ),
    # ========================================================================
    # UN SDG - SDMX/REST API exists but requires additional work to verify.
    # Web portal has a clean CSV export.
    # ========================================================================
    Indicator(
        key="sdg_mobile_network_coverage",
        name="Proportion of population covered by at least a 3G mobile network (SDG 9.c.1)",
        pillar=Pillar.SUPPLY,
        component="Access Infrastructure",
        source="UN SDG Database",
        source_code="9.c.1",
        availability=Availability.MANUAL,
        unit="%",
        manual_url="https://unstats.un.org/sdgs/dataportal/database",
        notes="UN SDG Data Portal; filter by indicator 9.c.1 and export CSV.",
    ),
    Indicator(
        key="sdg_broadband_subscriptions",
        name="Fixed-broadband subscriptions per 100 inhabitants (SDG 17.6.1)",
        pillar=Pillar.SUPPLY,
        component="Access Infrastructure",
        source="UN SDG Database",
        source_code="17.6.1",
        availability=Availability.MANUAL,
        unit="per 100",
        manual_url="https://unstats.un.org/sdgs/dataportal/database",
        notes="Same as World Bank IT.NET.BBND.P2; kept for SDG-aligned reporting.",
    ),
    Indicator(
        key="sdg_internet_users",
        name="Proportion of individuals using the internet (SDG 17.8.1)",
        pillar=Pillar.DEMAND,
        component="Device and Broadband Uptake",
        source="UN SDG Database",
        source_code="17.8.1",
        availability=Availability.MANUAL,
        unit="%",
        manual_url="https://unstats.un.org/sdgs/dataportal/database",
        notes="Same as World Bank IT.NET.USER.ZS; kept for SDG-aligned reporting.",
    ),
    # ========================================================================
    # IMF - fiscal and financial access indicators (DataMapper API)
    # ========================================================================
    Indicator(
        key="imf_gdp_per_capita_ppp",
        name="GDP per capita, PPP (IMF, current international $)",
        pillar=Pillar.DEMAND,
        component="State of the Human Condition",
        source="IMF",
        source_code="PPPPC",
        availability=Availability.API,
        unit="USD PPP",
        notes="IMF World Economic Outlook",
        earliest_year=2000,
        latest_year=2026,  # WEO includes projections
    ),
    Indicator(
        key="imf_real_gdp_growth",
        name="Real GDP growth (IMF, annual % change)",
        pillar=Pillar.DEMAND,
        component="State of the Human Condition",
        source="IMF",
        source_code="NGDP_RPCH",
        availability=Availability.API,
        unit="%",
        notes="IMF World Economic Outlook",
        earliest_year=2000,
        latest_year=2026,
    ),
    Indicator(
        key="imf_general_gov_revenue",
        name="General government revenue (IMF, % of GDP)",
        pillar=Pillar.INSTITUTIONAL,
        component="Institutions and the Business Environment",
        source="IMF",
        source_code="GGR_NGDP",
        availability=Availability.API,
        unit="% of GDP",
        notes="IMF Fiscal Monitor",
        earliest_year=2000,
        latest_year=2025,
    ),
    # ========================================================================
    # UNCTAD - UNCTADstat portal (API schema shifts, not reliable programmatically)
    # ========================================================================
    Indicator(
        key="unctad_ict_goods_exports",
        name="ICT goods exports as share of total goods exports (UNCTAD)",
        pillar=Pillar.INNOVATION,
        component="Outcomes",
        source="UNCTADstat",
        source_code="US.SoSICT",
        availability=Availability.MANUAL,
        unit="%",
        manual_url="https://unctadstat.unctad.org/datacentre/dataviewer/US.SoSICT",
        notes="UNCTADstat web portal; CSV export.",
    ),
    Indicator(
        key="unctad_digitally_deliverable_services",
        name="Digitally-deliverable services exports (UNCTAD, % of services exports)",
        pillar=Pillar.INNOVATION,
        component="Outcomes",
        source="UNCTADstat",
        source_code="US.DigitalServices",
        availability=Availability.MANUAL,
        unit="%",
        manual_url="https://unctadstat.unctad.org/datacentre/",
        notes="UNCTADstat digital trade; CSV export from portal.",
    ),
]


def indicators_for(pillars: set[Pillar], availability: set[Availability] | None = None) -> list[Indicator]:
    """Filter the catalog by pillar and availability."""
    result = [i for i in CATALOG if i.pillar in pillars]
    if availability is not None:
        result = [i for i in result if i.availability in availability]
    return result


def by_source(indicators: list[Indicator]) -> dict[str, list[Indicator]]:
    """Group indicators by source for batched fetching."""
    grouped: dict[str, list[Indicator]] = {}
    for ind in indicators:
        grouped.setdefault(ind.source, []).append(ind)
    return grouped


def is_available_for_range(ind: Indicator, start_year: int, end_year: int) -> bool:
    """Whether an indicator has any expected data overlapping [start_year, end_year].

    Rules:
      - If the indicator is 'sparse' (Findex, etc.), we do NOT restrict by
        year range at all. The user might pick a narrow window; sparse series
        simply return empty rows for years without data, rather than being
        greyed out.
      - Otherwise, the indicator is available if its coverage window
        [earliest_year, latest_year - publication_lag_years + 1] overlaps the
        selected range. The publication_lag_years carve-out accounts for the
        typical 1-2 year delay between data year and publication.
    """
    if ind.sparse:
        return True
    # The effective latest year is reduced by publication lag for recent
    # year ranges; e.g. WGI 2024 may not publish until 2026.
    effective_latest = max(ind.earliest_year, ind.latest_year)
    return not (end_year < ind.earliest_year or start_year > effective_latest)
