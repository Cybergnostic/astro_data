"""Antiscia and contra-antiscia helpers."""

from __future__ import annotations

from typing import List, Tuple

from ..models import PlanetPosition, ReflectionHit
from .dignity import degree_in_sign


def antiscia_longitude(longitude: float) -> float:
    """Mirror a longitude across the Cancer-Capricorn axis."""
    return (180.0 - longitude) % 360.0


def contra_antiscia_longitude(longitude: float) -> float:
    """Mirror a longitude across the Aries-Libra axis (opposite the antiscion)."""
    return (360.0 - longitude) % 360.0


def reflection_hits_for_planet(
    planet: PlanetPosition, planets: List[PlanetPosition]
) -> Tuple[List[ReflectionHit], List[ReflectionHit]]:
    """
    Return other planets that fall on this planet's antiscia or contra-antiscia.

    Rule: only exact degrees count (0–29 system). Two planets are linked if:
      - they are in the paired antiscia/contra-antiscia signs, AND
      - their integer degrees within the sign sum to 29 (minutes can differ).
    """
    target_antiscia = antiscia_longitude(planet.longitude)
    target_contra = contra_antiscia_longitude(planet.longitude)
    antiscia_sign = int(target_antiscia // 30) % 12
    contra_sign = int(target_contra // 30) % 12

    deg_in_sign_self = degree_in_sign(planet.longitude)
    deg_int_self = int(deg_in_sign_self)

    antiscia_hits: List[ReflectionHit] = []
    contra_hits: List[ReflectionHit] = []

    for other in planets:
        if other.name == planet.name:
            continue

        other_deg = degree_in_sign(other.longitude)
        other_deg_int = int(other_deg)
        degree_sum_ok = (deg_int_self + other_deg_int) == 29

        # Antiscia (solstice reflection)
        if degree_sum_ok and int(other.longitude // 30) % 12 == antiscia_sign:
            orb_antiscia = _shortest_distance(other.longitude, target_antiscia)
            antiscia_hits.append(ReflectionHit(other=other.name, orb=orb_antiscia, target_longitude=target_antiscia))

        # Contra-antiscia (equinox reflection)
        if degree_sum_ok and int(other.longitude // 30) % 12 == contra_sign:
            orb_contra = _shortest_distance(other.longitude, target_contra)
            contra_hits.append(ReflectionHit(other=other.name, orb=orb_contra, target_longitude=target_contra))

    antiscia_hits.sort(key=lambda hit: hit.orb)
    contra_hits.sort(key=lambda hit: hit.orb)
    return antiscia_hits, contra_hits


def _shortest_distance(a: float, b: float) -> float:
    """Return the minimal arc distance between two longitudes."""
    diff = abs(a - b) % 360.0
    return min(diff, 360.0 - diff)
