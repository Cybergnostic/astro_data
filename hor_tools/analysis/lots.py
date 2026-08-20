"""Arabic/Hermetic Lots supported by the course formula registry."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..models import Houses, PlanetPosition
from .aspects import ASPECTS, PLANET_ORBS, _aspect_angle_for_contact, _distance_to_aspect
from .dignity import SIGNS, SIGN_RULERS, sign_index_from_longitude


@dataclass(frozen=True)
class LotAspect:
    planet: str
    kind: str
    orb: float


@dataclass
class LotResult:
    name: str
    longitude: float
    sign: str
    house: int
    ruler: str
    ruler_longitude: float | None
    ruler_house: int | None
    ruler_sees_lot: bool
    aspects: list[LotAspect] = field(default_factory=list)
    group: str = "topical"
    formula: str = ""


@dataclass(frozen=True)
class UnsupportedLot:
    name: str
    reason: str


@dataclass
class LotsReport:
    hermetic: list[LotResult]
    topical: list[LotResult]
    unsupported: list[UnsupportedLot]

    @property
    def all_calculated(self) -> list[LotResult]:
        return [*self.hermetic, *self.topical]


def _lot(asc: float, add: float, subtract: float) -> float:
    return (asc + add - subtract) % 360.0


def _house_from_longitude(longitude: float, asc: float) -> int:
    asc_sign = sign_index_from_longitude(asc)
    sign = sign_index_from_longitude(longitude)
    return ((sign - asc_sign) % 12) + 1


def _sees_by_sign(source_longitude: float, target_longitude: float) -> bool:
    """Traditional sign sight: conjunction, sextile, square, trine or opposition."""
    source_sign = sign_index_from_longitude(source_longitude)
    target_sign = sign_index_from_longitude(target_longitude)
    distance = (target_sign - source_sign) % 12
    return distance in {0, 2, 3, 4, 6, 8, 9, 10}


def _planetary_aspects_to_lot(
    lot_longitude: float, planets: list[PlanetPosition]
) -> list[LotAspect]:
    """Return close degree contacts cast by planets to a passive Lot.

    Lots do not cast rays and have no orb of their own. The allowed orb is
    therefore the orb of the planet casting the ray, exactly as in the course.
    """
    hits: list[LotAspect] = []
    for planet in planets:
        allowed = PLANET_ORBS.get(planet.name, 0.0)
        angle = _aspect_angle_for_contact(planet.longitude, lot_longitude, allowed)
        if angle is None:
            continue
        orb = _distance_to_aspect(planet.longitude, lot_longitude, angle)
        hits.append(LotAspect(planet=planet.name, kind=ASPECTS[angle], orb=orb))
    return sorted(hits, key=lambda item: item.orb)


def _make_result(
    name: str,
    longitude: float,
    planets: list[PlanetPosition],
    houses: Houses,
    *,
    group: str,
    formula: str,
) -> LotResult:
    sign_idx = sign_index_from_longitude(longitude)
    ruler = SIGN_RULERS[sign_idx]
    by_name = {planet.name: planet for planet in planets}
    ruler_planet = by_name.get(ruler)
    aspects = _planetary_aspects_to_lot(longitude, planets)
    return LotResult(
        name=name,
        longitude=longitude,
        sign=SIGNS[sign_idx],
        house=_house_from_longitude(longitude, houses.asc),
        ruler=ruler,
        ruler_longitude=ruler_planet.longitude if ruler_planet else None,
        ruler_house=ruler_planet.house if ruler_planet else None,
        ruler_sees_lot=(
            _sees_by_sign(ruler_planet.longitude, longitude)
            if ruler_planet is not None
            else False
        ),
        aspects=aspects,
        group=group,
        formula=formula,
    )


def build_lots(
    planets: list[PlanetPosition],
    houses: Houses,
    is_day_chart: bool,
    native_male: bool | None = None,
) -> LotsReport:
    """Calculate the seven Hermetic Lots plus supported topical course Lots.

    The corpus contains two explicitly different Eros formulas: the seven-Lot
    Hermetic sequence derives Eros from Spirit, while the natal relationship
    formula registry derives a topical Eros from Fortune. Both are retained and
    labelled rather than silently conflated.

    Sensitive disease/death Lots are deliberately not calculated in the default
    technical report. The Hermes marriage Lot is calculated when the native's
    sex is available, because its formula is sex-specific but does not reverse
    by sect.
    """

    pos = {planet.name: planet.longitude for planet in planets}
    asc = houses.asc
    sun = pos["Sun"]
    moon = pos["Moon"]

    if is_day_chart:
        fortune = _lot(asc, moon, sun)
        spirit = _lot(asc, sun, moon)
        enemy = _lot(asc, fortune, pos["Saturn"])
        victory = _lot(asc, pos["Jupiter"], spirit)
        courage = _lot(asc, fortune, pos["Mars"])
        hermetic_eros = _lot(asc, pos["Venus"], spirit)
        necessity = _lot(asc, fortune, pos["Mercury"])
    else:
        fortune = _lot(asc, sun, moon)
        spirit = _lot(asc, moon, sun)
        enemy = _lot(asc, pos["Saturn"], fortune)
        victory = _lot(asc, spirit, pos["Jupiter"])
        courage = _lot(asc, pos["Mars"], fortune)
        hermetic_eros = _lot(asc, spirit, pos["Venus"])
        necessity = _lot(asc, pos["Mercury"], fortune)

    hermetic_values = [
        ("Fortune", fortune, "Asc + Moon - Sun" if is_day_chart else "Asc + Sun - Moon"),
        ("Spirit", spirit, "Asc + Sun - Moon" if is_day_chart else "Asc + Moon - Sun"),
        (
            "Enemy",
            enemy,
            "Asc + Fortune - Saturn" if is_day_chart else "Asc + Saturn - Fortune",
        ),
        (
            "Victory",
            victory,
            "Asc + Jupiter - Spirit" if is_day_chart else "Asc + Spirit - Jupiter",
        ),
        (
            "Courage",
            courage,
            "Asc + Fortune - Mars" if is_day_chart else "Asc + Mars - Fortune",
        ),
        (
            "Eros (Hermetic)",
            hermetic_eros,
            "Asc + Venus - Spirit" if is_day_chart else "Asc + Spirit - Venus",
        ),
        (
            "Necessity",
            necessity,
            "Asc + Fortune - Mercury" if is_day_chart else "Asc + Mercury - Fortune",
        ),
    ]
    hermetic = [
        _make_result(name, lon, planets, houses, group="hermetic", formula=formula)
        for name, lon, formula in hermetic_values
    ]

    def sect_formula(day_add: float, day_sub: float) -> tuple[float, str]:
        if is_day_chart:
            return _lot(asc, day_add, day_sub), "day formula"
        return _lot(asc, day_sub, day_add), "night formula (reversed)"

    topical_raw: list[tuple[str, float, str]] = []
    siblings, note = sect_formula(pos["Jupiter"], pos["Saturn"])
    topical_raw.append(
        ("Siblings", siblings, note + ": Asc + Jupiter - Saturn / reversed")
    )
    topical_raw.append(
        (
            "Number of siblings",
            _lot(asc, pos["Saturn"], pos["Mercury"]),
            "Asc + Saturn - Mercury",
        )
    )
    father, note = sect_formula(pos["Saturn"], sun)
    topical_raw.append(("Father", father, note + ": Asc + Saturn - Sun / reversed"))
    mother, note = sect_formula(moon, pos["Venus"])
    topical_raw.append(("Mother", mother, note + ": Asc + Moon - Venus / reversed"))
    topical_raw.append(
        ("Friends", _lot(asc, pos["Mercury"], moon), "Asc + Mercury - Moon")
    )

    ninth_cusp = houses.cusps[9] % 360.0
    ninth_ruler = SIGN_RULERS[sign_index_from_longitude(ninth_cusp)]
    topical_raw.append(
        (
            "Travel",
            _lot(asc, ninth_cusp, pos[ninth_ruler]),
            f"Asc + 9th House - {ninth_ruler}",
        )
    )

    if is_day_chart:
        knowledge = (pos["Mercury"] + pos["Jupiter"] - pos["Saturn"]) % 360.0
        k_formula = "Mercury + Jupiter - Saturn"
    else:
        knowledge = (pos["Mercury"] + pos["Saturn"] - pos["Jupiter"]) % 360.0
        k_formula = "Mercury + Saturn - Jupiter"
    topical_raw.append(("Knowledge", knowledge, k_formula))

    faith, note = sect_formula(pos["Mercury"], moon)
    topical_raw.append(("Faith", faith, note + ": Asc + Mercury - Moon / reversed"))
    children, note = sect_formula(pos["Saturn"], pos["Jupiter"])
    topical_raw.append(
        ("Children", children, note + ": Asc + Saturn - Jupiter / reversed")
    )
    daughters, note = sect_formula(pos["Venus"], pos["Jupiter"])
    topical_raw.append(
        ("Daughters", daughters, note + ": Asc + Venus - Jupiter / reversed")
    )
    sons, note = sect_formula(pos["Mercury"], pos["Jupiter"])
    topical_raw.append(("Sons", sons, note + ": Asc + Mercury - Jupiter / reversed"))

    if native_male is True:
        topical_raw.append(
            (
                "Marriage (Hermes — male)",
                _lot(asc, pos["Venus"], pos["Saturn"]),
                "Asc + Venus - Saturn (fixed; not reversed by sect)",
            )
        )
    elif native_male is False:
        topical_raw.append(
            (
                "Marriage (Hermes — female)",
                _lot(asc, pos["Saturn"], pos["Venus"]),
                "Asc + Saturn - Venus (fixed; not reversed by sect)",
            )
        )

    divorce, note = sect_formula(pos["Venus"], pos["Jupiter"])
    topical_raw.append(
        ("Divorce", divorce, note + ": Asc + Venus - Jupiter / reversed")
    )

    relationship_eros, note = sect_formula(pos["Venus"], fortune)
    topical_raw.append(
        (
            "Eros (relationship-course variant)",
            relationship_eros,
            note + ": Asc + Venus - Fortune / reversed",
        )
    )
    topical_raw.append(
        ("Profession", _lot(asc, moon, pos["Saturn"]), "Asc + Moon - Saturn")
    )

    topical = [
        _make_result(name, lon, planets, houses, group="topical", formula=formula)
        for name, lon, formula in topical_raw
    ]
    unsupported = []
    if native_male is None:
        unsupported.append(
            UnsupportedLot(
                "Marriage (Hermes)",
                "Course formula is sex-specific and no native-sex value was supplied.",
            )
        )
    unsupported.extend(
        [
            UnsupportedLot(
                "Death (Paul)",
                "Sensitive formula omitted from the default technical report.",
            ),
            UnsupportedLot(
                "Hermes disease",
                "Sensitive/variant formula omitted from the default technical report.",
            ),
        ]
    )
    return LotsReport(hermetic=hermetic, topical=topical, unsupported=unsupported)
