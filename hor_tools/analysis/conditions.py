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


def _last_jd_inside_moon_sign(
    start_jd: float, end_jd: float, moon_sign: int, iterations: int = 36
) -> float:
    """Bisect a step that crosses sign ingress and return a moment just inside.

    Using ephemeris positions avoids assuming perfectly linear lunar motion in
    the final step.  The returned lower bound remains on the original side of
    the sign boundary, so an aspect exact only at/after ingress is not counted.
    """
    low = start_jd
    high = end_jd
    for _ in range(iterations):
        mid = (low + high) / 2.0
        sign = int(_planet_longitude(mid, swe.MOON) // 30) % 12
        if sign == moon_sign:
            low = mid
        else:
            high = mid
    return low


def _aspect_crosses_between(previous: dict[str, float], current: dict[str, float]) -> bool:
    for other in _PLANET_IDS:
        if other == "Moon":
            continue
        rel0 = (previous[other] - previous["Moon"]) % 360.0
        rel1 = (current[other] - current["Moon"]) % 360.0
        if _crosses_major_aspect(rel0, rel1):
            return True
    return False


def moon_void_of_course(chart: ChartInput, moon: PlanetPosition, step_hours: float = 0.5) -> bool:
    """Return whether the Moon perfects no major aspect before leaving its sign.

    The search walks forward through ephemeris positions until sign egress and
    checks exact conjunction, sextile, square, trine or opposition perfection.
    If ingress occurs inside the final step, that step is bisected and aspects
    are checked up to a moment still inside the old sign before VOC is declared.
    """
    if moon.name != "Moon":
        raise ValueError("moon_void_of_course requires the Moon position")

    ensure_ephe_path()
    jd = julian_day_from_chart(chart)
    moon_sign = int(moon.longitude // 30) % 12
    step = step_hours / 24.0
    max_steps = int(5.0 * 24.0 / step_hours) + 2

    previous_jd = jd
    previous = {name: _planet_longitude(jd, body_id) for name, body_id in _PLANET_IDS.items()}

    for index in range(1, max_steps + 1):
        next_jd = jd + index * step
        current = {name: _planet_longitude(next_jd, body_id) for name, body_id in _PLANET_IDS.items()}

        if int(current["Moon"] // 30) % 12 != moon_sign:
            inside_jd = _last_jd_inside_moon_sign(previous_jd, next_jd, moon_sign)
            inside = {
                name: _planet_longitude(inside_jd, body_id)
                for name, body_id in _PLANET_IDS.items()
            }
            if _aspect_crosses_between(previous, inside):
                return False
            return True

        if _aspect_crosses_between(previous, current):
            return False

        previous_jd = next_jd
        previous = current

    # Defensive fallback: if ephemeris data somehow failed to show a lunar sign
    # egress inside five days, do not assert a void condition.
    return False
