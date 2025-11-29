from __future__ import annotations

from ..models import PlanetPosition
from .dignity import sign_index_from_longitude

DAY_PLANETS = {"Sun", "Jupiter", "Saturn"}
NIGHT_PLANETS = {"Moon", "Venus", "Mars"}


def chart_sect(sun_house: int) -> str:
    """Return 'day' if Sun is in houses 7 - 12 (above horizon), else 'night'."""
    return "day" if 7 <= sun_house <= 12 else "night"


def is_oriental(planet_long: float, sun_long: float) -> bool:
    """Planet oriental if it rises before Sun: longitude behind the Sun (0-180° short arc)."""
    delta = (sun_long - planet_long) % 360.0
    return 0 < delta < 180


def planet_sect(planet_name: str, oriental: bool) -> str:
    """
    Sun/Jupiter/Saturn = day
    Moon/Venus/Mars   = night
    Mercury: oriental = day; occidental = night
    """
    if planet_name == "Mercury":
        return "day" if oriental else "night"
    if planet_name in DAY_PLANETS:
        return "day"
    if planet_name in NIGHT_PLANETS:
        return "night"
    return "day"


def is_above_horizon(house: int) -> bool:
    """Approximation: houses 7 - 12 are above horizon."""
    return 7 <= house <= 12


def compute_hayz_and_halb(
    planet: PlanetPosition, sect_chart: str, sect_planet: str
) -> tuple[bool, bool]:
    """
    Halb: hemisphere match depends on both chart sect and planet sect.
      - Day planet: above horizon in a day chart; below in a night chart.
      - Night planet: below horizon in a day chart; above in a night chart.
    Hayz: requires Halb first, then sign gender matching planet sect:
      - Day planet in masculine signs (fire/air).
      - Night planet in feminine signs (earth/water).
    """
    above = is_above_horizon(planet.house)
    preferred = above if sect_chart == sect_planet else not above
    halb = preferred

    hayz = False
    if halb:
        sign_idx = sign_index_from_longitude(planet.longitude)
        masculine = (sign_idx % 2) == 0  # Aries, Gemini, Leo, Libra, Sagittarius, Aquarius
        if sect_planet == "day" and masculine:
            hayz = True
        if sect_planet == "night" and not masculine:
            hayz = True

    return hayz, halb
