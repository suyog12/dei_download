"""Shared types and helpers for source fetchers.

Every fetcher returns DataPoint rows. Country codes are ISO-3 where possible
so we can merge across sources without ambiguity.
"""

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class DataPoint:
    indicator_key: str
    indicator_name: str
    pillar: str
    component: str
    source: str
    country_iso3: str
    country_name: str
    year: int
    value: float | None
    unit: str = ""

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


class FetchError(Exception):
    """Raised when a source fetch fails in a recoverable way."""
