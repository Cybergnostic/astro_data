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
    # Extended relationship flags
    self_applying: bool = False  # Is this planet moving toward perfection?
    mutual_application: bool = False
    mutual_separation: bool = False
    counter_ray: bool = False


@dataclass
class InfluenceSource:
    """One source of bonification/maltreatment."""

    planet: str
    reason: str


@dataclass
class DominationInfo:
    """Sign-based domination/decimation relationship."""

    dominated: str
    dominator: str
    relationship: str
    sign_distance: int
    orb: float | None = None
    has_counter_ray: bool = False


@dataclass
class ReceptionInfo:
    """Reception or generosity exchange."""

    host: str
    guest: str
    dignities: list[str]
    aspect_kind: str | None = None


@dataclass
class TranslationOfLight:
    """Translation of light chain via a fast planet."""

    translator: str
    from_planet: str
    to_planet: str
    aspect_from: AspectInfo
    aspect_to: AspectInfo
    naturally_fastest: bool = False


@dataclass
class CollectionOfLight:
    """Collection of light gathered by a slower planet."""

    collector: str
    from_planets: tuple[str, str]
    aspect_from_first: AspectInfo
    aspect_from_second: AspectInfo
    collector_naturally_slower: bool = False
    naturally_fastest: str | None = None


@dataclass
class ChartRelationships:
    """Chart-level relationship aggregates."""

    dominations: list[DominationInfo]
    translations: list[TranslationOfLight]
    collections: list[CollectionOfLight]


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

    # Relationship flags
    bonification_sources: List[InfluenceSource]
    maltreatment_sources: List[InfluenceSource]
    is_bonified: bool
    is_maltreated: bool
    benefic_enclosure_by_ray: bool
    malefic_enclosure_by_ray: bool
    benefic_enclosure_by_sign: bool
    malefic_enclosure_by_sign: bool
    dominations_over: List[DominationInfo]
    dominated_by: List[DominationInfo]
    receptions_given: List[ReceptionInfo]
    receptions_received: List[ReceptionInfo]
    generosities_given: List[ReceptionInfo]
    generosities_received: List[ReceptionInfo]
    is_feral: bool
