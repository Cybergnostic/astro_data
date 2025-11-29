from __future__ import annotations

from typing import List

from ..models import PlanetPosition, AspectInfo

PLANET_ORBS = {
    "Saturn": 9.0,
    "Jupiter": 10.0,
    "Mars": 7.0,
    "Sun": 15.0,
    "Venus": 7.5,
    "Mercury": 7.0,
    "Moon": 12.0,
}

ASPECTS = {
    0.0: "conjunction",
    60.0: "sextile",
    90.0: "square",
    120.0: "trine",
    180.0: "opposition",
}
ASPECT_ANGLES = list(ASPECTS.keys())


def _shortest_distance(a: float, b: float) -> float:
    diff = abs(a - b)
    return min(diff, 360.0 - diff)


def aspects_for_planet(planet: PlanetPosition, all_planets: List[PlanetPosition]) -> List[AspectInfo]:
    infos: List[AspectInfo] = []
    for other in all_planets:
        if other.name == planet.name:
            continue

        distance = _shortest_distance(planet.longitude, other.longitude)

        # choose closest aspect angle
        best_angle = min(ASPECT_ANGLES, key=lambda ang: abs(distance - ang))
        kind = ASPECTS[best_angle]
        max_orb = max(PLANET_ORBS.get(planet.name, 0.0), PLANET_ORBS.get(other.name, 0.0))
        orb = abs(distance - best_angle)
        if orb > max_orb:
            continue  # no aspect

        applying = _is_applying(planet, other, best_angle)
        dexter = _is_dexter(planet.longitude, other.longitude, best_angle)

        infos.append(
            AspectInfo(
                other=other.name,
                kind=kind,
                orb=orb,
                applying=applying,
                dexter=dexter,
            )
        )
    return infos


def _is_applying(p1: PlanetPosition, p2: PlanetPosition, aspect_angle: float) -> bool:
    """
    Determine if the aspect between p1 and p2 is applying relative to the faster planet.

    1. Identify faster planet by |speed_long|.
    2. Measure separation from slower to faster.
    3. If the faster planet's motion reduces the difference to exact angle, it's applying.
    """
    # choose faster and slower
    if abs(p1.speed_long) >= abs(p2.speed_long):
        faster, slower = p1, p2
    else:
        faster, slower = p2, p1

    delta = (faster.longitude - slower.longitude) % 360.0
    # current difference to exact aspect
    diff_now = delta - aspect_angle
    # motion sign: +1 direct, -1 retrograde
    motion_sign = 1 if faster.speed_long >= 0 else -1

    # If motion_sign * diff_now < 0, faster is moving toward perfection
    return motion_sign * diff_now < 0


def _is_dexter(from_long: float, to_long: float, aspect_angle: float) -> bool:
    """
    Return True if aspect from 'from_long' to 'to_long' is dexter.

    Compute zodiacal separation from casting planet to receiving planet.
    If the receiving planet lies 'behind' the exact forward aspect point,
    we treat the ray as cast backward (dexter), otherwise forward (sinister).
    """
    delta = (to_long - from_long) % 360.0
    forward_diff = abs(delta - aspect_angle)
    backward_diff = abs((360.0 - delta) - aspect_angle)
    # If backward solution is closer, treat as dexter.
    return backward_diff < forward_diff
