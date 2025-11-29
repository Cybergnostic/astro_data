"""Dataclasses that capture the normalized chart data used throughout the project."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class SynodicPhaseInfo:
    group: str  # "superior", "inferior", "lunar", or "none"
    code: str   # short machine name
    index: int  # numeric phase index in that group
    label: str  # human-readable label


@dataclass
class ChartInput:
    """Normalized birth data derived from a Morinus .hor file."""

    name: str
    datetime_utc: datetime
    tz_offset_hours: float
    latitude: float
    longitude: float
    house_system: str
    zodiac: str


@dataclass
class PlanetPosition:
    """Computed placement for a single planet."""

    name: str
    longitude: float
    latitude: float
    speed_long: float
    speed_lat: float
    house: int
    retrograde: bool
    elongation_from_sun: float | None = None
    synodic_phase: SynodicPhaseInfo | None = None


@dataclass
class Houses:
    """Whole sign house cusps with Ascendant and MC coordinates."""

    cusps: list[float]
    asc: float
    mc: float | None


@dataclass
class AspectInfo:
    """Aspect from this planet to another body."""

    other: str
    kind: str
    orb: float
    applying: bool
    dexter: bool


@dataclass
class PlanetReport:
    """
    Full traditional analysis for a single planet.
    """

    planet: PlanetPosition

    # Essential dignity
    sign: str
    ruler: Optional[str]
    exaltation_lord: Optional[str]
    triplicity_lord: Optional[str]
    term_lord: Optional[str]
    face_lord: Optional[str]
    is_domicile: bool
    is_exalted: bool
    is_detriment: bool
    is_fall: bool

    # Sect / hayz / halb / oriental / occidental
    sect_chart: str
    sect_planet: str
    in_sect: bool
    hayz: bool
    halb: bool
    oriental: bool
    occidental: bool

    # Motion
    speed_ratio: float
    speed_class: str

    # Fixed stars
    fixed_stars: List[str]

    # Aspects
    aspects: List[AspectInfo]
