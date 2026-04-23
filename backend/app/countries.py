"""The 125 economies covered by the Digital Evolution Index 2025.

ISO-3 codes follow World Bank conventions. Regions match Tufts's DEI
classification (Asia Pacific, Europe & Central Asia, Latin America &
Caribbean, Middle East & Africa, North America).

We ship this as a static list rather than hitting the WB country API at
runtime so the country picker works even when WB is unreachable.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Country:
    iso3: str
    name: str
    region: str


DEI_COUNTRIES: list[Country] = [
    # Asia Pacific
    Country("AUS", "Australia", "Asia Pacific"),
    Country("BGD", "Bangladesh", "Asia Pacific"),
    Country("KHM", "Cambodia", "Asia Pacific"),
    Country("CHN", "China", "Asia Pacific"),
    Country("HKG", "Hong Kong SAR, China", "Asia Pacific"),
    Country("IND", "India", "Asia Pacific"),
    Country("IDN", "Indonesia", "Asia Pacific"),
    Country("JPN", "Japan", "Asia Pacific"),
    Country("LAO", "Lao PDR", "Asia Pacific"),
    Country("MYS", "Malaysia", "Asia Pacific"),
    Country("MNG", "Mongolia", "Asia Pacific"),
    Country("NPL", "Nepal", "Asia Pacific"),
    Country("NZL", "New Zealand", "Asia Pacific"),
    Country("PAK", "Pakistan", "Asia Pacific"),
    Country("PHL", "Philippines", "Asia Pacific"),
    Country("SGP", "Singapore", "Asia Pacific"),
    Country("KOR", "South Korea", "Asia Pacific"),
    Country("LKA", "Sri Lanka", "Asia Pacific"),
    Country("TWN", "Taiwan", "Asia Pacific"),
    Country("THA", "Thailand", "Asia Pacific"),
    Country("VNM", "Vietnam", "Asia Pacific"),

    # Europe & Central Asia
    Country("ALB", "Albania", "Europe & Central Asia"),
    Country("ARM", "Armenia", "Europe & Central Asia"),
    Country("AUT", "Austria", "Europe & Central Asia"),
    Country("AZE", "Azerbaijan", "Europe & Central Asia"),
    Country("BLR", "Belarus", "Europe & Central Asia"),
    Country("BEL", "Belgium", "Europe & Central Asia"),
    Country("BIH", "Bosnia & Herzegovina", "Europe & Central Asia"),
    Country("BGR", "Bulgaria", "Europe & Central Asia"),
    Country("HRV", "Croatia", "Europe & Central Asia"),
    Country("CYP", "Cyprus", "Europe & Central Asia"),
    Country("CZE", "Czechia", "Europe & Central Asia"),
    Country("DNK", "Denmark", "Europe & Central Asia"),
    Country("EST", "Estonia", "Europe & Central Asia"),
    Country("FIN", "Finland", "Europe & Central Asia"),
    Country("FRA", "France", "Europe & Central Asia"),
    Country("GEO", "Georgia", "Europe & Central Asia"),
    Country("DEU", "Germany", "Europe & Central Asia"),
    Country("GRC", "Greece", "Europe & Central Asia"),
    Country("HUN", "Hungary", "Europe & Central Asia"),
    Country("ISL", "Iceland", "Europe & Central Asia"),
    Country("IRL", "Ireland", "Europe & Central Asia"),
    Country("ITA", "Italy", "Europe & Central Asia"),
    Country("KAZ", "Kazakhstan", "Europe & Central Asia"),
    Country("KGZ", "Kyrgyzstan", "Europe & Central Asia"),
    Country("LVA", "Latvia", "Europe & Central Asia"),
    Country("LTU", "Lithuania", "Europe & Central Asia"),
    Country("LUX", "Luxembourg", "Europe & Central Asia"),
    Country("MLT", "Malta", "Europe & Central Asia"),
    Country("MDA", "Moldova", "Europe & Central Asia"),
    Country("MNE", "Montenegro", "Europe & Central Asia"),
    Country("NLD", "Netherlands", "Europe & Central Asia"),
    Country("MKD", "North Macedonia", "Europe & Central Asia"),
    Country("NOR", "Norway", "Europe & Central Asia"),
    Country("POL", "Poland", "Europe & Central Asia"),
    Country("PRT", "Portugal", "Europe & Central Asia"),
    Country("ROU", "Romania", "Europe & Central Asia"),
    Country("RUS", "Russia", "Europe & Central Asia"),
    Country("SRB", "Serbia", "Europe & Central Asia"),
    Country("SVK", "Slovakia", "Europe & Central Asia"),
    Country("SVN", "Slovenia", "Europe & Central Asia"),
    Country("ESP", "Spain", "Europe & Central Asia"),
    Country("SWE", "Sweden", "Europe & Central Asia"),
    Country("CHE", "Switzerland", "Europe & Central Asia"),
    Country("TUR", "Turkey", "Europe & Central Asia"),
    Country("UKR", "Ukraine", "Europe & Central Asia"),
    Country("GBR", "United Kingdom", "Europe & Central Asia"),
    Country("UZB", "Uzbekistan", "Europe & Central Asia"),

    # Latin America & Caribbean
    Country("ARG", "Argentina", "Latin America & Caribbean"),
    Country("BOL", "Bolivia", "Latin America & Caribbean"),
    Country("BRA", "Brazil", "Latin America & Caribbean"),
    Country("CHL", "Chile", "Latin America & Caribbean"),
    Country("COL", "Colombia", "Latin America & Caribbean"),
    Country("CRI", "Costa Rica", "Latin America & Caribbean"),
    Country("DOM", "Dominican Republic", "Latin America & Caribbean"),
    Country("ECU", "Ecuador", "Latin America & Caribbean"),
    Country("SLV", "El Salvador", "Latin America & Caribbean"),
    Country("GTM", "Guatemala", "Latin America & Caribbean"),
    Country("HND", "Honduras", "Latin America & Caribbean"),
    Country("JAM", "Jamaica", "Latin America & Caribbean"),
    Country("MEX", "Mexico", "Latin America & Caribbean"),
    Country("NIC", "Nicaragua", "Latin America & Caribbean"),
    Country("PAN", "Panama", "Latin America & Caribbean"),
    Country("PRY", "Paraguay", "Latin America & Caribbean"),
    Country("PER", "Peru", "Latin America & Caribbean"),
    Country("URY", "Uruguay", "Latin America & Caribbean"),
    Country("VEN", "Venezuela", "Latin America & Caribbean"),

    # Middle East & Africa
    Country("DZA", "Algeria", "Middle East & Africa"),
    Country("AGO", "Angola", "Middle East & Africa"),
    Country("BHR", "Bahrain", "Middle East & Africa"),
    Country("BEN", "Benin", "Middle East & Africa"),
    Country("BWA", "Botswana", "Middle East & Africa"),
    Country("CMR", "Cameroon", "Middle East & Africa"),
    Country("CIV", "Côte d'Ivoire", "Middle East & Africa"),
    Country("EGY", "Egypt", "Middle East & Africa"),
    Country("ETH", "Ethiopia", "Middle East & Africa"),
    Country("GHA", "Ghana", "Middle East & Africa"),
    Country("IRN", "Iran", "Middle East & Africa"),
    Country("IRQ", "Iraq", "Middle East & Africa"),
    Country("ISR", "Israel", "Middle East & Africa"),
    Country("JOR", "Jordan", "Middle East & Africa"),
    Country("KEN", "Kenya", "Middle East & Africa"),
    Country("KWT", "Kuwait", "Middle East & Africa"),
    Country("LBN", "Lebanon", "Middle East & Africa"),
    Country("MDG", "Madagascar", "Middle East & Africa"),
    Country("MWI", "Malawi", "Middle East & Africa"),
    Country("MLI", "Mali", "Middle East & Africa"),
    Country("MUS", "Mauritius", "Middle East & Africa"),
    Country("MAR", "Morocco", "Middle East & Africa"),
    Country("NAM", "Namibia", "Middle East & Africa"),
    Country("NGA", "Nigeria", "Middle East & Africa"),
    Country("OMN", "Oman", "Middle East & Africa"),
    Country("QAT", "Qatar", "Middle East & Africa"),
    Country("RWA", "Rwanda", "Middle East & Africa"),
    Country("SAU", "Saudi Arabia", "Middle East & Africa"),
    Country("SEN", "Senegal", "Middle East & Africa"),
    Country("ZAF", "South Africa", "Middle East & Africa"),
    Country("TZA", "Tanzania", "Middle East & Africa"),
    Country("TUN", "Tunisia", "Middle East & Africa"),
    Country("UGA", "Uganda", "Middle East & Africa"),
    Country("ARE", "United Arab Emirates", "Middle East & Africa"),
    Country("ZMB", "Zambia", "Middle East & Africa"),
    Country("ZWE", "Zimbabwe", "Middle East & Africa"),

    # North America
    Country("CAN", "Canada", "North America"),
    Country("USA", "United States", "North America"),
]


# Fast lookup by ISO-3
COUNTRY_BY_ISO3: dict[str, Country] = {c.iso3: c for c in DEI_COUNTRIES}


def is_dei_country(iso3: str) -> bool:
    return iso3 in COUNTRY_BY_ISO3
