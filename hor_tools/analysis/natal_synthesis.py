"""Deterministic natal-synthesis factors from the course.

This module deliberately separates algorithmic selection from astrological
judgment. Primary motivation and geniture expose their factors without
pretending to make the final synthesis; the ruler of behaviour is selected
where the course gives an explicit priority algorithm.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..almuten import ALMUTEN_PLANETS, essential_contributions_at_degree
from ..models import Houses, PlanetPosition, PlanetReport
from ..synodic import COMBUST_ORB_DEG, UNDER_BEAMS_ORB_DEG
from .aspects import ASPECTS, _aspect_angle_for_contact, _distance_to_aspect
from .dignity import SIGNS, SIGN_RULERS, sign_index_from_longitude
from .duads import dodekatemorion_longitude
from .sect import is_above_horizon

PRIMARY_CONTACT_ORB = 5.0
BEHAVIOUR_DUAD_ORB = 5.0

ELEMENT_BY_SIGN = {
    0: "fire", 1: "earth", 2: "air", 3: "water",
    4: "fire", 5: "earth", 6: "air", 7: "water",
    8: "fire", 9: "earth", 10: "air", 11: "water",
}
MOTIVATION_LABELS = {
    "fire": "power, success, independence and freedom",
    "air": "freedom of expression, exchange of information and movement",
    "water": "emotional security and stability",
    "earth": "material and physical security",
}
SIGN_MOTIVATION = {
    0: "initiative, ambition, conquest, freedom and independence",
    1: "accumulation and preservation of material values",
    2: "initiating conversation and free exchange of ideas and information",
    3: "initiating nurturing and protection",
    4: "accumulation of power, freedom, independence and authority",
    5: "investment, trading and exchange of material values",
    6: "accumulation of knowledge and free exchange of information",
    7: "absorption and retention of emotional contents",
    8: "power through energetic exchange and interaction with others",
    9: "initiating the acquisition of material security",
    10: "transmission of ideas and information and freedom of movement",
    11: "adaptation and release of emotional contents",
}
MERCURY_ELEMENT_LABELS = {
    "fire": "enthusiastic, positive and proud",
    "earth": "pragmatic, slow and deliberative",
    "air": "quick, curious, versatile and scattered",
    "water": "cautious, reserved and reflective",
}
ANGULAR_HOUSES = {1, 4, 7, 10}
SUCCEDENT_HOUSES = {2, 5, 8, 11}


@dataclass
class PrimaryMotivationFactor:
    source: str
    element: str
    motivation: str
    detail: str
    planet: str | None = None
    condition: list[str] = field(default_factory=list)


@dataclass
class PrimaryMotivationReport:
    factors: list[PrimaryMotivationFactor]
    elemental_counts: dict[str, int]
    note: str = "Factors only; final primary-motivation synthesis belongs to the astrologer."


@dataclass
class BehaviourRulerReport:
    primary: str | None
    secondary: str | None
    rule: str
    evidence: list[str]


@dataclass
class GenitureCandidate:
    planet: str
    house: int
    mundane_class: str
    essential_condition: list[str]
    accidental_condition: list[str]


@dataclass
class GenitureFactorsReport:
    candidates: list[GenitureCandidate]
    note: str = (
        "Lilly-style geniture requires qualitative comparison of mundane and essential "
        "strength; no mechanical winner is selected."
    )


@dataclass
class DegreeAlmuten:
    point: str
    longitude: float
    winners: list[str]
    score: int
    scores: dict[str, int]


@dataclass
class CompositeAlmuten:
    points: tuple[str, ...]
    winners: list[str]
    score: int
    scores: dict[str, int]


@dataclass
class MindFactorsReport:
    mercury: list[str]
    moon: list[str]
    mercury_almuten: DegreeAlmuten
    moon_almuten: DegreeAlmuten
    composite_almuten: CompositeAlmuten
    secondary_contacts: list[str]
    mercury_moon_relation: list[str]
    note: str = (
        "Formal factors/descriptors only. The composite Almuten is the summed dignity "
        "score of Mercury and Moon positions; its interpretive dominance still depends "
        "on condition and contact with the significators."
    )


def _element(longitude: float) -> str:
    return ELEMENT_BY_SIGN[sign_index_from_longitude(longitude)]


def _condition(report: PlanetReport) -> list[str]:
    result: list[str] = []
    if report.is_domicile:
        result.append("domicile")
    if report.is_exalted:
        result.append("exaltation")
    if report.is_detriment:
        result.append("detriment")
    if report.is_fall:
        result.append("fall")
    if not any(
        (report.is_domicile, report.is_exalted, report.is_detriment, report.is_fall)
    ):
        result.append("no major dignity/debility")
    result.append("in sect" if report.in_sect else "out of sect")
    if report.hayz:
        result.append("hayz")
    elif report.halb:
        result.append("halb")
    if report.planet.retrograde:
        result.append("retrograde")
    if report.planet.station:
        result.append(f"{report.planet.station} station")
    result.append(report.speed_class)
    if report.is_true_cazimi:
        result.append("true cazimi")
    elif report.is_cazimi:
        result.append("cazimi")
    if report.is_maltreated:
        result.append("maltreated")
    if report.is_bonified:
        result.append("bonified")
    return result


def _asc_ruler_condition(report: PlanetReport, asc_sign_name: str) -> list[str]:
    result = _condition(report)
    if any(
        item.domicile_sign == asc_sign_name and item.avoided
        for item in report.domicile_aversions
    ):
        result.append("in aversion to Ascendant sign")
    return result


def _contact(
    source_longitude: float, target_longitude: float, orb: float
) -> tuple[str, float] | None:
    angle = _aspect_angle_for_contact(source_longitude, target_longitude, orb)
    if angle is None:
        return None
    return ASPECTS[angle], _distance_to_aspect(
        source_longitude, target_longitude, angle
    )


def build_primary_motivation(
    planets: list[PlanetPosition], houses: Houses, reports: list[PlanetReport]
) -> PrimaryMotivationReport:
    """Return the source-defined factors used to judge primary motivation."""
    del planets
    by_name = {report.planet.name: report for report in reports}
    asc_sign = sign_index_from_longitude(houses.asc)
    asc_ruler = SIGN_RULERS[asc_sign]
    ruler_report = by_name[asc_ruler]
    factors: list[PrimaryMotivationFactor] = []

    asc_element = _element(houses.asc)
    factors.append(
        PrimaryMotivationFactor(
            source="Ascendant sign",
            element=asc_element,
            motivation=SIGN_MOTIVATION[asc_sign],
            detail=f"{SIGNS[asc_sign]} ({MOTIVATION_LABELS[asc_element]})",
        )
    )

    ruler_sign = sign_index_from_longitude(ruler_report.planet.longitude)
    ruler_element = ELEMENT_BY_SIGN[ruler_sign]
    factors.append(
        PrimaryMotivationFactor(
            source="Ascendant ruler",
            element=ruler_element,
            motivation=SIGN_MOTIVATION[ruler_sign],
            detail=f"{asc_ruler} in {ruler_report.sign}, House {ruler_report.planet.house}",
            planet=asc_ruler,
            condition=_asc_ruler_condition(ruler_report, SIGNS[asc_sign]),
        )
    )

    for report in reports:
        contact = _contact(
            report.planet.longitude, houses.asc, PRIMARY_CONTACT_ORB
        )
        if contact is None:
            continue
        kind, orb = contact
        sign_idx = sign_index_from_longitude(report.planet.longitude)
        element = ELEMENT_BY_SIGN[sign_idx]
        source = (
            "Planet on Ascendant" if kind == "conjunction" else "Aspect to Ascendant"
        )
        factors.append(
            PrimaryMotivationFactor(
                source=source,
                element=element,
                motivation=SIGN_MOTIVATION[sign_idx],
                detail=(
                    f"{report.planet.name} {kind}, orb {orb:.2f}° from {report.sign}"
                ),
                planet=report.planet.name,
                condition=_condition(report),
            )
        )

    counts = {element: 0 for element in MOTIVATION_LABELS}
    for factor in factors:
        counts[factor.element] += 1
    return PrimaryMotivationReport(factors=factors, elemental_counts=counts)


def _behaviour_evidence(
    primary: str,
    base_evidence: list[str],
    reports: list[PlanetReport],
    houses: Houses,
) -> list[str]:
    """Add course-required condition and supplementary behaviour factors."""
    by_name = {report.planet.name: report for report in reports}
    evidence = list(base_evidence)
    report = by_name[primary]
    evidence.append(f"{primary} condition: {', '.join(_condition(report))}")
    for star in report.fixed_stars:
        evidence.append(f"{primary} fixed-star contact: {star}")

    for candidate in reports:
        duad = dodekatemorion_longitude(candidate.planet.longitude)
        diff = abs((duad - houses.asc + 180.0) % 360.0 - 180.0)
        if diff <= BEHAVIOUR_DUAD_ORB:
            evidence.append(
                f"supplementary: {candidate.planet.name} duad on ASC, orb {diff:.2f}°"
            )
    return evidence


def build_behaviour_ruler(
    planets: list[PlanetPosition], houses: Houses, reports: list[PlanetReport]
) -> BehaviourRulerReport:
    """Apply the course's ruler-of-behaviour hierarchy without replacing duad supplements."""
    asc_ruler = SIGN_RULERS[sign_index_from_longitude(houses.asc)]
    by_name = {report.planet.name: report for report in reports}
    house_one = [planet for planet in planets if planet.house == 1]
    if house_one:
        winner = min(
            house_one,
            key=lambda planet: abs(
                (planet.longitude - houses.asc + 180.0) % 360.0 - 180.0
            ),
        )
        distance = abs(
            (winner.longitude - houses.asc + 180.0) % 360.0 - 180.0
        )
        return BehaviourRulerReport(
            primary=winner.name,
            secondary=asc_ruler if asc_ruler != winner.name else None,
            rule="planet in House I; nearest Ascendant has priority",
            evidence=_behaviour_evidence(
                winner.name,
                [f"{winner.name} in House I, {distance:.2f}° from ASC"],
                reports,
                houses,
            ),
        )

    conjunction_candidates: list[tuple[float, str, str]] = []
    for target in ("Mercury", "Moon"):
        target_report = by_name[target]
        for aspect in target_report.aspects:
            if aspect.kind == "conjunction":
                conjunction_candidates.append((aspect.orb, aspect.other, target))
    if conjunction_candidates:
        orb, winner, target = min(conjunction_candidates)
        return BehaviourRulerReport(
            primary=winner,
            secondary=asc_ruler if asc_ruler != winner else None,
            rule="no planet in House I; use planet conjunct Mercury or Moon",
            evidence=_behaviour_evidence(
                winner,
                [f"{winner} conjunct {target}, orb {orb:.2f}°"],
                reports,
                houses,
            ),
        )

    aspect_candidates: list[tuple[float, str, str, str]] = []
    for target in ("Mercury", "Moon"):
        target_report = by_name[target]
        for aspect in target_report.aspects:
            aspect_candidates.append(
                (aspect.orb, aspect.other, target, aspect.kind)
            )
    if aspect_candidates:
        orb, winner, target, kind = min(aspect_candidates)
        return BehaviourRulerReport(
            primary=winner,
            secondary=asc_ruler if asc_ruler != winner else None,
            rule=(
                "no House-I planet or conjunction; use closest aspect to Mercury or Moon"
            ),
            evidence=_behaviour_evidence(
                winner,
                [f"{winner} {kind} {target}, orb {orb:.2f}°"],
                reports,
                houses,
            ),
        )

    return BehaviourRulerReport(
        primary=asc_ruler,
        secondary=None,
        rule="no additional qualifying planet; Ascendant ruler remains the behaviour ruler",
        evidence=_behaviour_evidence(
            asc_ruler,
            ["Ascendant ruler remains when no House-I/Mercury/Moon candidate qualifies"],
            reports,
            houses,
        ),
    )


def build_geniture_factors(reports: list[PlanetReport]) -> GenitureFactorsReport:
    """Expose qualitative geniture evidence without manufacturing a score."""
    candidates: list[GenitureCandidate] = []
    for report in reports:
        house = report.planet.house
        if house in ANGULAR_HOUSES:
            mundane = "angular"
        elif house in SUCCEDENT_HOUSES:
            mundane = "succedent"
        else:
            mundane = "cadent"
        essential = [
            item
            for item in _condition(report)
            if item
            in {
                "domicile",
                "exaltation",
                "detriment",
                "fall",
                "no major dignity/debility",
            }
        ]
        accidental = [item for item in _condition(report) if item not in essential]
        candidates.append(
            GenitureCandidate(
                planet=report.planet.name,
                house=house,
                mundane_class=mundane,
                essential_condition=essential,
                accidental_condition=accidental,
            )
        )
    rank = {"angular": 0, "succedent": 1, "cadent": 2}
    candidates.sort(key=lambda item: (rank[item.mundane_class], item.house))
    return GenitureFactorsReport(candidates=candidates)


def _degree_almuten(
    point: str, longitude: float, is_day_chart: bool
) -> DegreeAlmuten:
    contributions = essential_contributions_at_degree(longitude, is_day_chart)
    scores = {
        planet: sum(contributions[planet]) for planet in ALMUTEN_PLANETS
    }
    maximum = max(scores.values(), default=0)
    winners = [
        planet
        for planet, score in scores.items()
        if score == maximum and score > 0
    ]
    return DegreeAlmuten(
        point=point,
        longitude=longitude,
        winners=winners,
        score=maximum,
        scores=scores,
    )


def _composite_almuten(
    points: tuple[tuple[str, float], ...], is_day_chart: bool
) -> CompositeAlmuten:
    scores = {planet: 0 for planet in ALMUTEN_PLANETS}
    for _name, longitude in points:
        contributions = essential_contributions_at_degree(longitude, is_day_chart)
        for planet in ALMUTEN_PLANETS:
            scores[planet] += sum(contributions[planet])
    maximum = max(scores.values(), default=0)
    winners = [
        planet
        for planet, score in scores.items()
        if score == maximum and score > 0
    ]
    return CompositeAlmuten(
        points=tuple(name for name, _longitude in points),
        winners=winners,
        score=maximum,
        scores=scores,
    )


def build_mind_factors(
    chart,
    reports: list[PlanetReport],
) -> MindFactorsReport:
    """Return Mercury/Moon factors and the course's topical Almuten of Mind."""
    by_name = {report.planet.name: report for report in reports}
    mercury = by_name["Mercury"]
    moon = by_name["Moon"]
    is_day = mercury.sect_chart == "day"
    mercury_element = _element(mercury.planet.longitude)
    mercury_dispositor = by_name[mercury.ruler]
    moon_dispositor = by_name[moon.ruler]

    mercury_items = [
        f"{mercury.sign}, House {mercury.planet.house}",
        f"element: {mercury_element} — {MERCURY_ELEMENT_LABELS[mercury_element]}",
        (
            "above horizon: easier expression and communication"
            if is_above_horizon(chart, mercury.planet)
            else "below horizon: more resourceful and reflective"
        ),
    ]
    if mercury.oriental:
        mercury_items.append("oriental: more direct, open and free")
    elif mercury.occidental:
        mercury_items.append(
            "occidental: more reflective, closed and conservative"
        )

    elongation = mercury.planet.elongation_from_sun
    if elongation is not None:
        if elongation <= COMBUST_ORB_DEG:
            mercury_items.append(
                "combust: dispersion; mind can get lost in irrelevant details"
            )
        elif elongation <= UNDER_BEAMS_ORB_DEG:
            mercury_items.append(
                "under beams: dispersion; mind can get lost in irrelevant details"
            )

    if mercury.speed_class == "swift":
        mercury_items.append("swift: quick and penetrating, but less persistent")
    elif mercury.speed_class == "slow":
        mercury_items.append("slow: slower, hesitant, fewer ideas")
    if mercury.planet.retrograde:
        mercury_items.append("retrograde: indecisive, changeable, rebellious")
    elif mercury.planet.station:
        mercury_items.append(f"{mercury.planet.station} station")
    else:
        mercury_items.append("direct: objective, less hesitation")
    mercury_items.extend(f"condition: {item}" for item in _condition(mercury))
    mercury_items.append(
        f"dispositor: {mercury_dispositor.planet.name} in {mercury_dispositor.sign}, "
        f"House {mercury_dispositor.planet.house}"
    )
    mercury_items.extend(
        f"dispositor condition: {item}" for item in _condition(mercury_dispositor)
    )

    moon_items = [
        f"{moon.sign}, House {moon.planet.house}",
        f"dispositor: {moon_dispositor.planet.name} in {moon_dispositor.sign}, "
        f"House {moon_dispositor.planet.house}",
        *[f"condition: {item}" for item in _condition(moon)],
        *[
            f"dispositor condition: {item}"
            for item in _condition(moon_dispositor)
        ],
    ]
    if moon.planet.synodic_phase:
        moon_items.append(f"phase: {moon.planet.synodic_phase.label}")

    secondary: list[str] = []
    seen: set[tuple[str, str]] = set()
    for target in (mercury, moon):
        for aspect in target.aspects:
            key = tuple(sorted((target.planet.name, aspect.other)))
            if key in seen:
                continue
            seen.add(key)
            if aspect.kind == "conjunction" or aspect.orb <= 6.0:
                secondary.append(
                    f"{target.planet.name} {aspect.kind} {aspect.other}, orb {aspect.orb:.2f}°"
                )

    mercury_almuten = _degree_almuten(
        "Mercury", mercury.planet.longitude, is_day
    )
    moon_almuten = _degree_almuten("Moon", moon.planet.longitude, is_day)
    composite_almuten = _composite_almuten(
        (
            ("Mercury", mercury.planet.longitude),
            ("Moon", moon.planet.longitude),
        ),
        is_day,
    )

    relation: list[str] = []
    merc_moon = next(
        (aspect for aspect in mercury.aspects if aspect.other == "Moon"), None
    )
    if merc_moon:
        relation.append(
            f"Mercury {merc_moon.kind} Moon, orb {merc_moon.orb:.2f}°"
        )
    else:
        relation.append("Mercury and Moon: no major degree contact")
    for reception in mercury.receptions_given:
        if reception.guest == "Moon":
            relation.append(
                f"Mercury receives Moon by {', '.join(reception.dignities)}"
            )
    for reception in moon.receptions_given:
        if reception.guest == "Mercury":
            relation.append(
                f"Moon receives Mercury by {', '.join(reception.dignities)}"
            )
    for repulsion in mercury.repulsions_given:
        if repulsion.guest == "Moon":
            relation.append(
                f"Mercury repels Moon by {', '.join(repulsion.debilities)}"
            )
    for repulsion in moon.repulsions_given:
        if repulsion.guest == "Mercury":
            relation.append(
                f"Moon repels Mercury by {', '.join(repulsion.debilities)}"
            )
    relation.append(
        "Composite Almuten of Mind: "
        + (", ".join(composite_almuten.winners) or "—")
        + f" ({composite_almuten.score})"
    )

    return MindFactorsReport(
        mercury=mercury_items,
        moon=moon_items,
        mercury_almuten=mercury_almuten,
        moon_almuten=moon_almuten,
        composite_almuten=composite_almuten,
        secondary_contacts=secondary,
        mercury_moon_relation=relation,
    )
