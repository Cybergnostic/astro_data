from __future__ import annotations

import swisseph as swe

from ..astro_engine import julian_day_from_chart
from ..models import ChartInput, PlanetPosition
from .dignity import sign_index_from_longitude

DAY_PLANETS = {"Sun", "Jupiter", "Saturn"}
NIGHT_PLANETS = {"Moon", "Venus", "Mars"}


def true_altitude(chart: ChartInput, planet: PlanetPosition) -> float:
    """Return the body's true geometric altitude above the local horizon."""
    jd_ut = julian_day_from_chart(chart)
    geopos = (chart.longitude, chart.latitude, chart.altitude_m or 0.0)
    _azimuth, altitude, _apparent_altitude = swe.azalt(
        jd_ut,
        swe.ECL2HOR,
        geopos,
        0.0,
        15.0,
        (planet.longitude, planet.latitude, 1.0),
    )
    return float(altitude)


def is_above_horizon(chart: ChartInput, planet: PlanetPosition) -> bool:
    """Use the actual astronomical horizon, not the whole-sign house number."""
    return true_altitude(chart, planet) > 0.0


def chart_sect(chart: ChartInput, sun: PlanetPosition) -> str:
    """Return day/night sect from the Sun's actual position relative to the horizon."""
    return "day" if is_above_horizon(chart, sun) else "night"


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


def compute_hayz_and_halb(
    planet: PlanetPosition,
    chart: ChartInput,
    sect_chart: str,
    sect_planet: str,
) -> tuple[bool, bool]:
    """
    Halb: hemisphere match depends on chart sect and planet sect.
      - In a day chart, day planets belong above and night planets below.
      - In a night chart, night planets belong above and day planets below.
    Hayz: requires Halb first, then sign gender matching planet sect:
      - Day planet in masculine signs (fire/air).
      - Night planet in feminine signs (earth/water).

    The hemisphere test uses the body's true altitude, so a planet near the
    Ascendant/Descendant is not misclassified merely because Whole Sign puts it
    in house 1 or 7.
    """
    above = is_above_horizon(chart, planet)
    if sect_chart == "day":
        halb = above if sect_planet == "day" else not above
    else:
        halb = above if sect_planet == "night" else not above

    hayz = False
    if halb:
        sign_idx = sign_index_from_longitude(planet.longitude)
        masculine = (sign_idx % 2) == 0
        if sect_planet == "day" and masculine:
            hayz = True
        if sect_planet == "night" and not masculine:
            hayz = True

    return hayz, halb
