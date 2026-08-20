from __future__ import annotations

from itertools import combinations
from typing import Dict, Iterable, List, Tuple

from .dignity import MEAN_SPEED, dignity_holders_for_position, sign_index_from_longitude
from ..models import (
    AspectInfo,
    ChartRelationships,
    CollectionOfLight,
    DominationInfo,
    InfluenceSource,
    PlanetPosition,
    PlanetReport,
    ReceptionInfo,
    TranslationOfLight,
)

BENEFICS = {"Jupiter", "Venus"}
MALEFICS = {"Mars", "Saturn"}
ASPECT_FOR_DOMINATION = {8: "trine", 9: "square", 10: "sextile"}


def aspect_lookup(reports: list[PlanetReport]) -> Dict[Tuple[str, str], AspectInfo]:
    """Build a fast lookup of aspects keyed by (source, target)."""
    lookup: Dict[Tuple[str, str], AspectInfo] = {}
    for rep in reports:
        for asp in rep.aspects:
            lookup[(rep.planet.name, asp.other)] = asp
    return lookup


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

            # Aktinobolia is not mere geometry: the overcoming planet must be
            # applying and the counter-ray must be close (within 3°).
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


def compute_enclosures(
    planets: list[PlanetPosition], lookup: Dict[Tuple[str, str], AspectInfo]
) -> Dict[str, dict[str, object]]:
    """Compute enclosure by sign and by ray for each planet."""
    sign_map: dict[int, list[str]] = {}
    for p in planets:
        sign_map.setdefault(sign_index_from_longitude(p.longitude), []).append(p.name)

    by_sign: dict[str, dict[str, bool]] = {}
    for p in planets:
        idx = sign_index_from_longitude(p.longitude)
        prev_planets = sign_map.get((idx - 1) % 12, [])
        next_planets = sign_map.get((idx + 1) % 12, [])
        by_sign[p.name] = {
            "benefic_sign": any(pl in BENEFICS for pl in prev_planets)
            and any(pl in BENEFICS for pl in next_planets),
            "malefic_sign": any(pl in MALEFICS for pl in prev_planets)
            and any(pl in MALEFICS for pl in next_planets),
        }

    positions = {p.name: p.longitude for p in planets}
    by_ray: dict[str, dict[str, list[str]]] = {
        p.name: {"benefic_ray": [], "malefic_ray": []} for p in planets
    }
    for target in planets:
        candidates = _aspecting_planets(target.name, lookup)
        if not candidates:
            continue
        ahead = _nearest_ahead(target.name, candidates, positions)
        behind = _nearest_behind(target.name, candidates, positions)
        for other in (ahead, behind):
            if not other:
                continue
            if other in BENEFICS:
                by_ray[target.name]["benefic_ray"].append(other)
            if other in MALEFICS:
                by_ray[target.name]["malefic_ray"].append(other)

    merged: Dict[str, dict[str, object]] = {}
    for p in planets:
        merged[p.name] = {
            "benefic_sign": by_sign[p.name]["benefic_sign"],
            "malefic_sign": by_sign[p.name]["malefic_sign"],
            "benefic_ray": by_ray[p.name]["benefic_ray"],
            "malefic_ray": by_ray[p.name]["malefic_ray"],
        }
    return merged


def _qualifies_for_reception(dignities: list[str]) -> bool:
    """Course threshold for reception and generosity."""
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

        asp = _get_pair_aspect(host.name, guest.name, lookup)
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


def compute_translation_of_light(
    planets: list[PlanetPosition], lookup: Dict[Tuple[str, str], AspectInfo]
) -> list[TranslationOfLight]:
    """Translation: a faster planet separates from one and applies to another."""
    translations: list[TranslationOfLight] = []
    names = [p.name for p in planets]
    speed_map = {p.name: abs(p.speed_long) for p in planets}

    for translator in planets:
        for from_name in names:
            if from_name == translator.name:
                continue
            asp_from = lookup.get((translator.name, from_name))
            if not asp_from or asp_from.self_applying:
                continue
            for to_name in names:
                if to_name in {translator.name, from_name}:
                    continue
                asp_to = lookup.get((translator.name, to_name))
                if not asp_to or not asp_to.self_applying:
                    continue
                if not _is_fastest(translator.name, [from_name, to_name], speed_map):
                    continue
                # In the course definition translation links two planets that
                # are not themselves directly connected.
                if _get_pair_aspect(from_name, to_name, lookup):
                    continue
                naturally_fastest = _is_fastest(
                    translator.name, [from_name, to_name], MEAN_SPEED
                )
                translations.append(
                    TranslationOfLight(
                        translator=translator.name,
                        from_planet=from_name,
                        to_planet=to_name,
                        aspect_from=asp_from,
                        aspect_to=asp_to,
                        naturally_fastest=naturally_fastest,
                    )
                )
    return translations


def compute_collection_of_light(
    planets: list[PlanetPosition], lookup: Dict[Tuple[str, str], AspectInfo]
) -> list[CollectionOfLight]:
    """Allow any third planet slower than both applying feeders to collect light."""
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
            collections.append(
                CollectionOfLight(
                    collector=collector.name,
                    from_planets=(first.name, second.name),
                    aspect_from_first=asp_first,
                    aspect_from_second=asp_second,
                    collector_naturally_slower=(
                        collector_mean < first_mean and collector_mean < second_mean
                    ),
                    naturally_fastest=(first.name if first_mean > second_mean else second.name),
                )
            )

    return collections


def compute_bonification_and_maltreatment(
    reports: list[PlanetReport],
    lookup: Dict[Tuple[str, str], AspectInfo],
    dominations: list[DominationInfo],
    enclosures: Dict[str, dict[str, object]],
) -> None:
    """Populate bonification/maltreatment sources on PlanetReport objects."""
    dom_by_target: dict[str, list[DominationInfo]] = {}
    dom_by_actor: dict[str, list[DominationInfo]] = {}
    for dom in dominations:
        dom_by_target.setdefault(dom.dominated, []).append(dom)
        dom_by_actor.setdefault(dom.dominator, []).append(dom)

    for rep in reports:
        bon: list[InfluenceSource] = []
        mal: list[InfluenceSource] = []
        name = rep.planet.name

        def add(target_list: list[InfluenceSource], planet: str, reason: str) -> None:
            if not any(src.planet == planet and src.reason == reason for src in target_list):
                target_list.append(InfluenceSource(planet=planet, reason=reason))

        for asp in rep.aspects:
            if asp.other in BENEFICS:
                add(bon, asp.other, f"ray_{asp.kind}")
                if asp.self_applying:
                    add(bon, asp.other, "applying")
                if asp.kind == "trine":
                    add(bon, asp.other, "benefic_trine")
            if asp.other in MALEFICS:
                add(mal, asp.other, f"ray_{asp.kind}")
                if asp.self_applying:
                    add(mal, asp.other, "applying")
                if asp.kind == "opposition":
                    add(mal, asp.other, "malefic_opposition")

        # Corporeal co-presence/contact within 3°.
        for other_rep in reports:
            if other_rep.planet.name == name:
                continue
            if sign_index_from_longitude(other_rep.planet.longitude) != sign_index_from_longitude(rep.planet.longitude):
                continue
            if _shortest_distance(rep.planet.longitude, other_rep.planet.longitude) <= 3.0:
                if other_rep.planet.name in BENEFICS:
                    add(bon, other_rep.planet.name, "conjunction")
                if other_rep.planet.name in MALEFICS:
                    add(mal, other_rep.planet.name, "conjunction")

        for dom in dom_by_target.get(name, []):
            if dom.dominator in BENEFICS:
                add(bon, dom.dominator, f"domination_{dom.relationship}")
            if dom.dominator in MALEFICS:
                add(mal, dom.dominator, f"domination_{dom.relationship}")

        for dom in dom_by_actor.get(name, []):
            if dom.has_counter_ray:
                if dom.dominated in BENEFICS:
                    add(bon, dom.dominated, f"counter_domination_{dom.relationship}")
                if dom.dominated in MALEFICS:
                    add(mal, dom.dominated, f"counter_domination_{dom.relationship}")

        if rep.ruler in BENEFICS:
            add(bon, rep.ruler, "dispositor")
        if rep.ruler in MALEFICS:
            add(mal, rep.ruler, "dispositor")

        enclosure = enclosures.get(name, {})
        if enclosure.get("benefic_sign"):
            add(bon, "benefics", "enclosure_by_sign")
        if enclosure.get("benefic_ray"):
            sources = ", ".join(enclosure.get("benefic_ray", []))
            add(bon, sources or "benefics", "enclosure_by_ray")
        if enclosure.get("malefic_sign"):
            add(mal, "malefics", "enclosure_by_sign")
        if enclosure.get("malefic_ray"):
            sources = ", ".join(enclosure.get("malefic_ray", []))
            add(mal, sources or "malefics", "enclosure_by_ray")

        rep.bonification_sources = bon
        rep.maltreatment_sources = mal
        rep.is_bonified = bool(bon)
        rep.is_maltreated = bool(mal)


def compute_feral(planets: list[PlanetPosition]) -> set[str]:
    """Return planets making no whole-sign sextile/square/trine/opposition."""
    feral: set[str] = set()
    sign_map = {p.name: sign_index_from_longitude(p.longitude) for p in planets}
    for p in planets:
        sees_other = False
        for other in planets:
            if other.name == p.name:
                continue
            diff = (sign_map[other.name] - sign_map[p.name]) % 12
            angle = min(diff, 12 - diff) * 30
            if angle in {60, 90, 120, 180}:
                sees_other = True
                break
        if not sees_other:
            feral.add(p.name)
    return feral


def aggregate_relationships(
    reports: list[PlanetReport], planets: list[PlanetPosition], is_day_chart: bool
) -> ChartRelationships:
    """Top-level helper to compute all chart-level relationships."""
    lookup = aspect_lookup(reports)
    dominations = compute_domination(planets, lookup)
    enclosures = compute_enclosures(planets, lookup)
    receptions = compute_receptions_and_generosity(planets, lookup, is_day_chart)
    translations = compute_translation_of_light(planets, lookup)
    collections = compute_collection_of_light(planets, lookup)
    compute_bonification_and_maltreatment(reports, lookup, dominations, enclosures)

    feral = compute_feral(planets)
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


def _get_pair_aspect(
    a: str,
    b: str,
    lookup: Dict[Tuple[str, str], AspectInfo],
    desired_kind: str | None = None,
) -> AspectInfo | None:
    asp = lookup.get((a, b)) or lookup.get((b, a))
    if asp and desired_kind and asp.kind != desired_kind:
        return None
    return asp


def _aspecting_planets(target: str, lookup: Dict[Tuple[str, str], AspectInfo]) -> List[str]:
    names = set()
    for src, other in lookup:
        if src == target:
            names.add(other)
        if other == target:
            names.add(src)
    return list(names)


def _nearest_ahead(target: str, others: Iterable[str], positions: Dict[str, float]) -> str | None:
    ahead = sorted(
        ((positions[o] - positions[target]) % 360.0, o)
        for o in others
        if o != target and positions[o] != positions[target]
    )
    return ahead[0][1] if ahead else None


def _nearest_behind(target: str, others: Iterable[str], positions: Dict[str, float]) -> str | None:
    behind = sorted(
        ((positions[target] - positions[o]) % 360.0, o)
        for o in others
        if o != target and positions[o] != positions[target]
    )
    return behind[0][1] if behind else None


def _is_fastest(candidate: str, others: list[str], speed_map: dict[str, float]) -> bool:
    cand_speed = speed_map.get(candidate, 0.0)
    return all(cand_speed > speed_map.get(other, 0.0) for other in others)


def _shortest_distance(a: float, b: float) -> float:
    diff = abs(a - b) % 360.0
    return min(diff, 360.0 - diff)
