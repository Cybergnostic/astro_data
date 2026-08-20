from __future__ import annotations

from itertools import combinations
from typing import Dict, List, Tuple

from .dignity import MEAN_SPEED, dignity_holders_for_position, sign_index_from_longitude
from .ray_geometry import (
    casters_with_ray_in_sign,
    has_intervening_ray,
    nearest_rays_in_sign,
)
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

            # Aktinobolia: the planet that overcomes must itself be applying and
            # be struck by the dominated planet's close counter-ray.
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


def _opposite_category_on_each_side(
    behind: tuple[float, str, str] | None,
    ahead: tuple[float, str, str] | None,
    category: set[str],
) -> list[str]:
    if not behind or not ahead:
        return []
    behind_name = behind[1]
    ahead_name = ahead[1]
    if behind_name == ahead_name:
        return []
    if behind_name in category and ahead_name in category:
        return [behind_name, ahead_name]
    return []


def _category_across_adjacent_signs(
    previous: set[str], next_: set[str], category: set[str]
) -> bool:
    return any(
        first != second and first in category and second in category
        for first in previous
        for second in next_
    )


def _malefic_enclosure_relieved(
    target_name: str, lookup: Dict[Tuple[str, str], AspectInfo]
) -> bool:
    """Sun or a benefic looking within <7° cancels malefic enclosure."""
    for reliever in {"Sun", "Jupiter", "Venus"} - {target_name}:
        asp = _get_pair_aspect(target_name, reliever, lookup)
        if asp and asp.orb < 7.0:
            return True
    return False


def compute_enclosures(
    planets: list[PlanetPosition], lookup: Dict[Tuple[str, str], AspectInfo]
) -> Dict[str, dict[str, object]]:
    """Compute degree/ray and sign enclosure from exact ray landing points.

    For enclosure by degree, the nearest body/ray on either side of the target
    inside its sign must come from the two benefics or the two malefics.  Taking
    the nearest ray on each side means any intervening third ray automatically
    breaks the enclosure, exactly as the course examples require.

    Sign enclosure likewise accepts a planet *or its ray* in the signs before
    and after the target.  A close (<7°) aspect from the Sun or a benefic cancels
    either type of malefic enclosure.
    """
    result: Dict[str, dict[str, object]] = {}

    for target in planets:
        idx = sign_index_from_longitude(target.longitude)
        previous_casters = casters_with_ray_in_sign((idx - 1) % 12, planets, target.name)
        next_casters = casters_with_ray_in_sign((idx + 1) % 12, planets, target.name)

        benefic_sign = _category_across_adjacent_signs(previous_casters, next_casters, BENEFICS)
        malefic_sign = _category_across_adjacent_signs(previous_casters, next_casters, MALEFICS)

        behind, ahead = nearest_rays_in_sign(target, planets)
        benefic_ray = _opposite_category_on_each_side(behind, ahead, BENEFICS)
        malefic_ray = _opposite_category_on_each_side(behind, ahead, MALEFICS)

        if (malefic_sign or malefic_ray) and _malefic_enclosure_relieved(target.name, lookup):
            malefic_sign = False
            malefic_ray = []

        result[target.name] = {
            "benefic_sign": benefic_sign,
            "malefic_sign": malefic_sign,
            "benefic_ray": benefic_ray,
            "malefic_ray": malefic_ray,
        }

    return result


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
    """Translation: fast planet separates from one and next applies to another.

    A ray/body of a fourth planet reached before the intended applying contact
    interrupts the translation.  The two principal planets may themselves have
    an aspect; the course says translation is then less necessary, not invalid.
    """
    translations: list[TranslationOfLight] = []
    names = [p.name for p in planets]
    by_name = {p.name: p for p in planets}
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

                if has_intervening_ray(
                    translator,
                    by_name[to_name],
                    asp_to.kind,
                    planets,
                    excluded_names={from_name, to_name},
                ):
                    continue

                translations.append(
                    TranslationOfLight(
                        translator=translator.name,
                        from_planet=from_name,
                        to_planet=to_name,
                        aspect_from=asp_from,
                        aspect_to=asp_to,
                        naturally_fastest=_is_fastest(
                            translator.name, [from_name, to_name], MEAN_SPEED
                        ),
                    )
                )

    return translations


def compute_collection_of_light(
    planets: list[PlanetPosition], lookup: Dict[Tuple[str, str], AspectInfo]
) -> list[CollectionOfLight]:
    """Collection by a slower third planet, provided it is each feeder's next contact."""
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

            # The collector must be the next relevant contact for BOTH feeders.
            # The other feeder is intentionally not excluded: if Moon reaches
            # Venus before Saturn, for example, the collection is cut.
            if has_intervening_ray(
                first,
                collector,
                asp_first.kind,
                planets,
                excluded_names={collector.name},
            ):
                continue
            if has_intervening_ray(
                second,
                collector,
                asp_second.kind,
                planets,
                excluded_names={collector.name},
            ):
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


def _is_fastest(candidate: str, others: list[str], speed_map: dict[str, float]) -> bool:
    cand_speed = speed_map.get(candidate, 0.0)
    return all(cand_speed > speed_map.get(other, 0.0) for other in others)


def _shortest_distance(a: float, b: float) -> float:
    diff = abs(a - b) % 360.0
    return min(diff, 360.0 - diff)
