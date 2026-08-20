from __future__ import annotations

from typing import List

from ..models import PlanetPosition, AspectInfo

# These are the teacher-specific planetary orbs used by this project.
# Do not replace them with the public/course handout table.
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
    diff = abs(a - b) % 360.0
    return min(diff, 360.0 - diff)


def _distance_to_aspect(lon1: float, lon2: float, aspect_angle: float) -> float:
    """Return the absolute orb from the nearest branch of an aspect."""
    separation = _shortest_distance(lon1, lon2)
    return abs(separation - aspect_angle)


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
        self_applying = _is_self_applying(planet, other, best_angle)
        other_applying = _is_self_applying(other, planet, best_angle)
        mutual_application = self_applying and other_applying
        mutual_separation = (not self_applying) and (not other_applying)

        infos.append(
            AspectInfo(
                other=other.name,
                kind=kind,
                orb=orb,
                applying=applying,
                dexter=dexter,
                self_applying=self_applying,
                mutual_application=mutual_application,
                mutual_separation=mutual_separation,
            )
        )
    return infos


def _is_applying(p1: PlanetPosition, p2: PlanetPosition, aspect_angle: float) -> bool:
    """
    Determine whether the two moving planets are approaching perfection.

    Compare the current orb with the orb a short time later while moving BOTH
    planets by their signed longitudinal speeds. This avoids the old 0°/360°
    wrap bug and automatically handles both branches of sextiles, squares and
    trines, as well as retrograde motion.
    """
    if abs(p1.speed_long - p2.speed_long) < 1e-12:
        return False

    dt_days = 0.01
    orb_now = _distance_to_aspect(p1.longitude, p2.longitude, aspect_angle)
    future_p1 = (p1.longitude + p1.speed_long * dt_days) % 360.0
    future_p2 = (p2.longitude + p2.speed_long * dt_days) % 360.0
    orb_future = _distance_to_aspect(future_p1, future_p2, aspect_angle)
    return orb_future < orb_now - 1e-12


def _is_dexter(from_long: float, to_long: float, aspect_angle: float) -> bool:
    """
    Return True if aspect from 'from_long' to 'to_long' is dexter.

    Compute zodiacal separation from casting planet to receiving planet.
    If the receiving planet lies closer to the backward aspect branch, the ray
    is dexter; otherwise it is sinister.
    """
    delta = (to_long - from_long) % 360.0
    forward_diff = abs(delta - aspect_angle)
    backward_diff = abs((360.0 - delta) - aspect_angle)
    return backward_diff < forward_diff


def _is_self_applying(moving: PlanetPosition, static: PlanetPosition, aspect_angle: float) -> bool:
    """
    Determine if ``moving`` is heading toward perfection with ``static`` while
    holding the latter fixed. The calculation is circular and works across 0°.
    """
    if abs(moving.speed_long) < 1e-12:
        return False

    dt_days = 0.01
    orb_now = _distance_to_aspect(moving.longitude, static.longitude, aspect_angle)
    future_long = (moving.longitude + moving.speed_long * dt_days) % 360.0
    orb_future = _distance_to_aspect(future_long, static.longitude, aspect_angle)
    return orb_future < orb_now - 1e-12
