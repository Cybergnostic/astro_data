from __future__ import annotations

"""Source-checked relationship rules layered over the shared relationship helpers.

This module keeps the established enclosure/translation/bonification machinery but
replaces the rules that were found to disagree with the distilled course material:
reception/generosity thresholds, collection of light, and aktinobolia/counter-ray.
"""

from itertools import combinations
from typing import Dict, Tuple

from . import relationships as base
from .dignity import MEAN_SPEED, dignity_holders_for_position, sign_index_from_longitude
from ..models import (
    AspectInfo,
    ChartRelationships,
    CollectionOfLight,
    DominationInfo,
    PlanetPosition,
    PlanetReport,
    ReceptionInfo,
)

ASPECT_FOR_DOMINATION = {8: "trine", 9: "square", 10: "sextile"}


def _qualifies_for_reception(dignities: list[str]) -> bool:
    """Course threshold for reception/generosity.

    A single high dignity (domicile or exaltation) is sufficient. Lesser
    dignities must occur in one of the accepted pairs: triplicity+term,
    triplicity+face, or term+face.
    """
    held = set(dignities)
    if "domicile" in held or "exaltation" in held:
        return True
    return any(
        pair <= held
        for pair in (
            {"triplicity", "term"},
            {"triplicity", "face"},
            {"term", "face"},
        )
    )


def compute_domination(
    planets: list[PlanetPosition], lookup: Dict[Tuple[str, str], AspectInfo]
) -> list[DominationInfo]:
    """Return sign-based domination and source-correct aktinobolia flags."""
    doms: list[DominationInfo] = []
    sign_map = {p.name: sign_index_from_longitude(p.longitude) for p in planets}

    for dominated in planets:
        dom_sign = sign_map[dominated.name]
        for dominator in planets:
            if dominator.name == dominated.name:
                continue
            dist = (sign_map[dominator.name] - dom_sign) % 12
            relationship = ASPECT_FOR_DOMINATION.get(dist)
            if not relationship:
                continue

            info = DominationInfo(
                dominated=dominated.name,
                dominator=dominator.name,
                relationship=f"{relationship}_decimation",
                sign_distance=dist,
            )

            # Aktinobolia is not just geometry: the overcoming/dominating planet
            # must be applying, and the counter-ray must be within 3°.
            asp = lookup.get((dominator.name, dominated.name))
            if asp and asp.kind == relationship and asp.self_applying and asp.orb <= 3.0:
                info.has_counter_ray = True
                info.orb = asp.orb
                asp.counter_ray = True
                other_view = lookup.get((dominated.name, dominator.name))
                if other_view:
                    other_view.counter_ray = True

            doms.append(info)

    return doms


def compute_receptions_and_generosity(
    planets: list[PlanetPosition],
    lookup: Dict[Tuple[str, str], AspectInfo],
    is_day_chart: bool,
) -> dict[str, dict[str, list[ReceptionInfo]]]:
    """Compute reception/generosity using the course's dignity threshold."""
    positions = {p.name: p.longitude for p in planets}
    result: dict[str, dict[str, list[ReceptionInfo]]] = {
        p.name: {
            "receptions_given": [],
            "receptions_received": [],
            "generosities_given": [],
            "generosities_received": [],
        }
        for p in planets
    }

    def register(host: PlanetPosition, guest: PlanetPosition) -> None:
        holders = dignity_holders_for_position(positions[guest.name], is_day_chart)
        dignities = [kind for kind, ruler in holders.items() if ruler == host.name]
        if not _qualifies_for_reception(dignities):
            return

        asp = base._get_pair_aspect(host.name, guest.name, lookup)
        info = ReceptionInfo(
            host=host.name,
            guest=guest.name,
            dignities=dignities,
            aspect_kind=asp.kind if asp else None,
        )
        if asp:
            result[host.name]["receptions_given"].append(info)
            result[guest.name]["receptions_received"].append(info)
        else:
            result[host.name]["generosities_given"].append(info)
            result[guest.name]["generosities_received"].append(info)

    for first, second in combinations(planets, 2):
        register(first, second)
        register(second, first)

    return result


def compute_collection_of_light(
    planets: list[PlanetPosition], lookup: Dict[Tuple[str, str], AspectInfo]
) -> list[CollectionOfLight]:
    """Allow any planet slower than both applying feeders to collect light."""
    collections: list[CollectionOfLight] = []
    speed_map = {p.name: abs(p.speed_long) for p in planets}

    for collector in planets:
        feeders = [p for p in planets if p.name != collector.name]
        for first, second in combinations(feeders, 2):
            asp_first = lookup.get((first.name, collector.name))
            asp_second = lookup.get((second.name, collector.name))
            if not (asp_first and asp_second):
                continue
            if not (asp_first.self_applying and asp_second.self_applying):
                continue
            if speed_map[collector.name] >= speed_map[first.name]:
                continue
            if speed_map[collector.name] >= speed_map[second.name]:
                continue

            collector_mean = MEAN_SPEED.get(collector.name, float("inf"))
            first_mean = MEAN_SPEED.get(first.name, float("inf"))
            second_mean = MEAN_SPEED.get(second.name, float("inf"))
            collector_natural = collector_mean < first_mean and collector_mean < second_mean
            naturally_fastest = first.name if first_mean > second_mean else second.name

            collections.append(
                CollectionOfLight(
                    collector=collector.name,
                    from_planets=(first.name, second.name),
                    aspect_from_first=asp_first,
                    aspect_from_second=asp_second,
                    collector_naturally_slower=collector_natural,
                    naturally_fastest=naturally_fastest,
                )
            )

    return collections


def aggregate_relationships(
    reports: list[PlanetReport], planets: list[PlanetPosition], is_day_chart: bool
) -> ChartRelationships:
    """Build chart relationships using corrected source-backed rules."""
    lookup = base.aspect_lookup(reports)
    dominations = compute_domination(planets, lookup)
    enclosures = base.compute_enclosures(planets, lookup)
    receptions = compute_receptions_and_generosity(planets, lookup, is_day_chart)
    translations = base.compute_translation_of_light(planets, lookup)
    collections = compute_collection_of_light(planets, lookup)
    base.compute_bonification_and_maltreatment(reports, lookup, dominations, enclosures)

    feral = base.compute_feral(planets)
    for rep in reports:
        name = rep.planet.name
        rep.dominations_over = [d for d in dominations if d.dominator == name]
        rep.dominated_by = [d for d in dominations if d.dominated == name]
        rep.benefic_enclosure_by_sign = bool(enclosures.get(name, {}).get("benefic_sign"))
        rep.malefic_enclosure_by_sign = bool(enclosures.get(name, {}).get("malefic_sign"))
        rep.benefic_enclosure_by_ray = bool(enclosures.get(name, {}).get("benefic_ray"))
        rep.malefic_enclosure_by_ray = bool(enclosures.get(name, {}).get("malefic_ray"))
        rep.receptions_given = receptions[name]["receptions_given"]
        rep.receptions_received = receptions[name]["receptions_received"]
        rep.generosities_given = receptions[name]["generosities_given"]
        rep.generosities_received = receptions[name]["generosities_received"]
        rep.is_feral = name in feral

    return ChartRelationships(
        dominations=dominations,
        translations=translations,
        collections=collections,
    )
