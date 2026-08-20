from __future__ import annotations

from typing import List

from ..models import PlanetPosition, AspectInfo

# Project-specific working orbs explicitly supplied for this calculator.
# The distilled course handout table differs for Jupiter/Mars/Venus
# (9/8/7), but this project deliberately uses 10/7/7.5 for those planets.
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

# In the course, configurations are sign relationships first and degree contacts
# second. A configuration/conjunction may continue across a sign boundary only
# very tightly; the deterministic project rule uses the stated 3° maximum.
OUT_OF_SIGN_MAX_ORB = 3.0
SIGN_ASPECT_ANGLES = {
    0: 0.0,
    2: 60.0,
    3: 90.0,
    4: 120.0,
    6: 180.0,
    8: 120.0,
    9: 90.0,
    10: 60.0,
}


def _shortest_distance(a: float, b: float) -> float:
    diff = abs(a - b) % 360.0
    return min(diff, 360.0 - diff)


def _distance_to_aspect(lon1: float, lon2: float, aspect_angle: float) -> float:
    """Return the absolute orb from the nearest branch of an aspect."""
    separation = _shortest_distance(lon1, lon2)
    return abs(separation - aspect_angle)


def _sign_aspect_angle(lon1: float, lon2: float) -> float | None:
    """Return the major aspect implied by the planets' current signs."""
    sign1 = int((lon1 % 360.0) // 30.0)
    sign2 = int((lon2 % 360.0) // 30.0)
    return SIGN_ASPECT_ANGLES.get((sign2 - sign1) % 12)


def _aspect_angle_for_contact(
    lon1: float,
    lon2: float,
    max_orb: float,
) -> float | None:
    """Choose the source-valid aspect for a planetary contact.

    The current whole-sign relationship determines the normal configuration.
    That configuration becomes an actual degree contact only when the planets
    enter the larger planetary orb. If the degree geometry still belongs to the
    immediately preceding/following configuration after a sign boundary, retain
    that out-of-sign contact only within 3° of exactness.
    """
    sign_angle = _sign_aspect_angle(lon1, lon2)
    if sign_angle is not None:
        sign_orb = _distance_to_aspect(lon1, lon2, sign_angle)
        if sign_orb <= max_orb:
            return sign_angle

    distance = _shortest_distance(lon1, lon2)
    geometric_angle = min(ASPECT_ANGLES, key=lambda ang: abs(distance - ang))
    geometric_orb = abs(distance - geometric_angle)

    # A different degree-aspect than the current sign configuration can only be
    # a carried contact across a sign boundary, and the course limits it to 3°.
    if geometric_angle != sign_angle and geometric_orb <= OUT_OF_SIGN_MAX_ORB:
        return geometric_angle

    return None


def aspects_for_planet(planet: PlanetPosition, all_planets: List[PlanetPosition]) -> List[AspectInfo]:
    infos: List[AspectInfo] = []
    for other in all_planets:
        if other.name == planet.name:
            continue

        max_orb = max(PLANET_ORBS.get(planet.name, 0.0), PLANET_ORBS.get(other.name, 0.0))
        aspect_angle = _aspect_angle_for_contact(planet.longitude, other.longitude, max_orb)
        if aspect_angle is None:
            continue

        kind = ASPECTS[aspect_angle]
        orb = _distance_to_aspect(planet.longitude, other.longitude, aspect_angle)
        applying = _is_applying(planet, other, aspect_angle)
        dexter = _is_dexter(planet.longitude, other.longitude, aspect_angle)
        self_applying = _is_self_applying(planet, other, aspect_angle)
        other_applying = _is_self_applying(other, planet, aspect_angle)
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
