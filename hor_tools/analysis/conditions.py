from __future__ import annotations

"""Additional accidental conditions explicitly used by the course material.

These conditions are kept as separate testimony instead of being collapsed into
one numerical score: house joy and latitude describe accidental strength, while
via combusta and void-of-course are separate condition/impediment flags.
"""

import swisseph as swe

from ..astro_engine import ensure_ephe_path, julian_day_from_chart
from ..models import ChartInput, PlanetPosition

PLANETARY_JOYS = {
    "Mercury": 1,
    "Moon": 3,
    "Venus": 5,
    "Mars": 6,
    "Sun": 9,
    "Jupiter": 11,
    "Saturn": 12,
}

# Formal course notes identify the especially harmful/burning core as the arc
# from the Sun's fall degree to the Moon's fall degree: 19° Libra to 3° Scorpio.
VIA_COMBUSTA_START = 180.0 + 19.0
VIA_COMBUSTA_END = 210.0 + 3.0

_MAJOR_ASPECTS = (0.0, 60.0, 90.0, 120.0, 180.0)
_PLANET_IDS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
}


def is_in_planetary_joy(planet: PlanetPosition) -> bool:
    return PLANETARY_JOYS.get(planet.name) == planet.house


def latitude_condition(planet: PlanetPosition, epsilon: float = 1e-9) -> str:
    """Return the course's simple north/south accidental-strength testimony."""
    if planet.latitude > epsilon:
        return "north_strengthening"
    if planet.latitude < -epsilon:
        return "south_weakening"
    return "on_ecliptic"


def is_in_via_combusta(longitude: float) -> bool:
    """Return True in the course's formal 19° Libra–3° Scorpio core."""
    lon = longitude % 360.0
    return VIA_COMBUSTA_START <= lon <= VIA_COMBUSTA_END


def _planet_longitude(jd_ut: float, body_id: int) -> float:
    result = swe.calc_ut(jd_ut, body_id, swe.FLG_SWIEPH | swe.FLG_SPEED)
    pos = result[0] if len(result) == 2 and isinstance(result[0], (tuple, list)) else result
    return float(pos[0]) % 360.0


def _unwrap_near(value: float, reference: float) -> float:
    while value - reference > 180.0:
        value -= 360.0
    while value - reference <= -180.0:
        value += 360.0
    return value


def _crosses_major_aspect(rel0: float, rel1: float) -> bool:
    """Whether a directed relative longitude crosses an exact major aspect."""
    rel1_u = _unwrap_near(rel1, rel0)
    lo, hi = sorted((rel0, rel1_u))
    for aspect in _MAJOR_ASPECTS:
        branches = {aspect % 360.0, (-aspect) % 360.0}
        for branch in branches:
            for turn in (-1, 0, 1, 2):
                target = branch + 360.0 * turn
                if lo <= target <= hi:
                    return True
    return False


def moon_void_of_course(chart: ChartInput, moon: PlanetPosition, step_hours: float = 0.5) -> bool:
    """Return whether the Moon perfects no major aspect before leaving its sign.

    This is evaluated from ephemeris positions rather than from a static orb or
    the Moon's current speed. The search walks forward until the Moon changes
    zodiacal sign and looks for exact conjunction, sextile, square, trine or
    opposition perfection to the other traditional planets. A 30-minute step is
    safely small for the Moon; crossings are detected on the unwrapped relative
    angle, so 0°/360° and the negative branches of aspects are handled.
    """
    if moon.name != "Moon":
        raise ValueError("moon_void_of_course requires the Moon position")

    ensure_ephe_path()
    jd = julian_day_from_chart(chart)
    moon_sign = int(moon.longitude // 30) % 12
    step = step_hours / 24.0
    # Five days is comfortably longer than the Moon can remain in one sign.
    max_steps = int(5.0 * 24.0 / step_hours) + 2

    previous = {name: _planet_longitude(jd, body_id) for name, body_id in _PLANET_IDS.items()}

    for index in range(1, max_steps + 1):
        next_jd = jd + index * step
        current = {name: _planet_longitude(next_jd, body_id) for name, body_id in _PLANET_IDS.items()}

        if int(current["Moon"] // 30) % 12 != moon_sign:
            return True

        for other in _PLANET_IDS:
            if other == "Moon":
                continue
            rel0 = (previous[other] - previous["Moon"]) % 360.0
            rel1 = (current[other] - current["Moon"]) % 360.0
            if _crosses_major_aspect(rel0, rel1):
                return False

        previous = current

    # Defensive fallback: if ephemeris data somehow failed to show a lunar sign
    # egress inside five days, do not assert a void condition.
    return False
