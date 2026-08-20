"""Geometric helpers for traditional planetary rays.

The relationship doctrines in this project are defined by where exact Ptolemaic
rays land in the zodiac, not by the bodily longitude of the planet casting the
ray.  Keeping the geometry here lets translation, collection and enclosure use
one consistent implementation.
"""

from __future__ import annotations

from math import inf
from typing import Iterable

from ..models import PlanetPosition

ASPECT_ANGLE_BY_KIND = {
    "conjunction": 0.0,
    "sextile": 60.0,
    "square": 90.0,
    "trine": 120.0,
    "opposition": 180.0,
}

_EPS = 1e-9


def ray_longitudes(caster_longitude: float, kind: str | None = None) -> list[tuple[str, float]]:
    """Return exact zodiacal landing points of a planet's body/major rays.

    Conjunction is the planet's body itself.  Sextile, square and trine cast two
    rays, one to either side; opposition has one unique landing point.
    """
    kinds = [kind] if kind is not None else list(ASPECT_ANGLE_BY_KIND)
    result: list[tuple[str, float]] = []
    seen: set[tuple[str, int]] = set()

    for aspect_kind in kinds:
        if aspect_kind not in ASPECT_ANGLE_BY_KIND:
            raise ValueError(f"Unknown aspect kind: {aspect_kind}")
        angle = ASPECT_ANGLE_BY_KIND[aspect_kind]
        if angle == 0.0:
            points = [caster_longitude % 360.0]
        elif angle == 180.0:
            points = [(caster_longitude + 180.0) % 360.0]
        else:
            points = [
                (caster_longitude + angle) % 360.0,
                (caster_longitude - angle) % 360.0,
            ]

        for point in points:
            # Rounded integer key only de-duplicates floating representations of
            # the same exact point; the original float is retained for geometry.
            key = (aspect_kind, round(point * 1_000_000_000))
            if key not in seen:
                seen.add(key)
                result.append((aspect_kind, point))

    return result


def directed_distance(moving: PlanetPosition, target_longitude: float) -> float:
    """Arc in degrees from ``moving`` to a longitude in its current direction."""
    if moving.speed_long > _EPS:
        return (target_longitude - moving.longitude) % 360.0
    if moving.speed_long < -_EPS:
        return (moving.longitude - target_longitude) % 360.0
    return inf


def distance_to_aspect_ray(
    moving: PlanetPosition, caster: PlanetPosition, aspect_kind: str
) -> float:
    """Distance until ``moving`` reaches the caster's relevant exact ray."""
    return min(
        directed_distance(moving, longitude)
        for _kind, longitude in ray_longitudes(caster.longitude, aspect_kind)
    )


def has_intervening_ray(
    moving: PlanetPosition,
    target_caster: PlanetPosition,
    target_kind: str,
    planets: Iterable[PlanetPosition],
    excluded_names: set[str] | None = None,
) -> bool:
    """Whether another body/ray is reached before the intended target ray.

    ``excluded_names`` controls which principal planets are not allowed to
    interrupt their own relationship.  Translation excludes both principals;
    collection deliberately does *not* exclude the other feeder, because the
    course explicitly says a feeder contacting the other feeder first cuts the
    collection.
    """
    excluded = set(excluded_names or ())
    target_distance = distance_to_aspect_ray(moving, target_caster, target_kind)
    if target_distance == inf:
        return False

    for caster in planets:
        if caster.name == moving.name or caster.name in excluded:
            continue
        for _kind, ray_longitude in ray_longitudes(caster.longitude):
            travel = directed_distance(moving, ray_longitude)
            if _EPS < travel < target_distance - _EPS:
                return True
    return False


def nearest_rays_in_sign(
    target: PlanetPosition, planets: Iterable[PlanetPosition]
) -> tuple[tuple[float, str, str] | None, tuple[float, str, str] | None]:
    """Nearest exact body/ray behind and ahead of target inside its zodiacal sign.

    Returned tuples are ``(distance, caster_name, aspect_kind)``.  Because the
    nearest ray on each side is used, a third planet's intervening ray naturally
    breaks a degree enclosure.
    """
    sign_index = int(target.longitude // 30) % 12
    target_degree = target.longitude % 30.0
    behind: list[tuple[float, str, str]] = []
    ahead: list[tuple[float, str, str]] = []

    for caster in planets:
        if caster.name == target.name:
            continue
        for aspect_kind, longitude in ray_longitudes(caster.longitude):
            if int(longitude // 30) % 12 != sign_index:
                continue
            degree = longitude % 30.0
            if degree < target_degree - _EPS:
                behind.append((target_degree - degree, caster.name, aspect_kind))
            elif degree > target_degree + _EPS:
                ahead.append((degree - target_degree, caster.name, aspect_kind))

    nearest_behind = min(behind, default=None, key=lambda item: item[0])
    nearest_ahead = min(ahead, default=None, key=lambda item: item[0])
    return nearest_behind, nearest_ahead


def casters_with_ray_in_sign(
    sign_index: int, planets: Iterable[PlanetPosition], excluded_name: str | None = None
) -> set[str]:
    """Names of planets whose body or major ray lands in ``sign_index``."""
    casters: set[str] = set()
    for caster in planets:
        if caster.name == excluded_name:
            continue
        for _kind, longitude in ray_longitudes(caster.longitude):
            if int(longitude // 30) % 12 == sign_index % 12:
                casters.add(caster.name)
                break
    return casters
