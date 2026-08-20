"""Assemble the complete deterministic natal technical worksheet."""

from __future__ import annotations

from dataclasses import dataclass

from ..almuten import build_almuten_figuris
from ..almuten_types import AlmutenResult
from ..models import ChartInput, ChartRelationships, Houses, PlanetPosition, PlanetReport
from .dignity import SIGNS, SIGN_RULERS, sign_index_from_longitude
from .duads import DuadPosition, dodekatemorion
from .lots import LotsReport, build_lots
from .natal_synthesis import (
    BehaviourRulerReport,
    GenitureFactorsReport,
    MindFactorsReport,
    PrimaryMotivationReport,
    build_behaviour_ruler,
    build_geniture_factors,
    build_mind_factors,
    build_primary_motivation,
)
from .solar import SolarFrame, planetary_day_hour_rulers, solar_frame_for_chart
from .temperament import TemperamentReport, build_temperament


@dataclass(frozen=True)
class NamedDuad:
    name: str
    source_longitude: float
    duad: DuadPosition


@dataclass(frozen=True)
class HouseStructure:
    house: int
    sign: str
    ruler: str
    ruler_house: int
    occupants: tuple[str, ...]


@dataclass
class NatalTechnicalReport:
    solar: SolarFrame
    day_ruler: str
    hour_ruler: str
    almuten: AlmutenResult
    lots: LotsReport
    duads: list[NamedDuad]
    houses: list[HouseStructure]
    temperament: TemperamentReport
    primary_motivation: PrimaryMotivationReport
    behaviour: BehaviourRulerReport
    geniture: GenitureFactorsReport
    mind: MindFactorsReport
    syzygy_longitude: float


def _duads(
    planets: list[PlanetPosition], houses: Houses, lots: LotsReport
) -> list[NamedDuad]:
    items = [
        NamedDuad(planet.name, planet.longitude, dodekatemorion(planet.longitude))
        for planet in planets
    ]
    items.append(NamedDuad("Ascendant", houses.asc, dodekatemorion(houses.asc)))
    if houses.mc is not None:
        items.append(NamedDuad("MC", houses.mc, dodekatemorion(houses.mc)))
    for lot in lots.all_calculated:
        items.append(NamedDuad(f"Lot: {lot.name}", lot.longitude, dodekatemorion(lot.longitude)))
    return items


def _house_structure(
    planets: list[PlanetPosition], houses: Houses
) -> list[HouseStructure]:
    by_name = {planet.name: planet for planet in planets}
    result: list[HouseStructure] = []
    for house in range(1, 13):
        sign_idx = sign_index_from_longitude(houses.cusps[house])
        ruler = SIGN_RULERS[sign_idx]
        occupants = tuple(planet.name for planet in planets if planet.house == house)
        result.append(
            HouseStructure(
                house=house,
                sign=SIGNS[sign_idx],
                ruler=ruler,
                ruler_house=by_name[ruler].house,
                occupants=occupants,
            )
        )
    return result


def build_natal_technical_report(
    chart: ChartInput,
    planets: list[PlanetPosition],
    houses: Houses,
    reports: list[PlanetReport],
    relationships: ChartRelationships,
) -> NatalTechnicalReport:
    """Calculate all source-backed technical sections for one natal chart."""

    del relationships  # relationships are already reflected into PlanetReport objects
    solar = solar_frame_for_chart(chart)
    day_ruler, hour_ruler = planetary_day_hour_rulers(chart)
    almuten = build_almuten_figuris(chart, planets, houses)
    lots = build_lots(planets, houses, solar.is_day, chart.male)
    almuten_name = almuten.almuten[0] if len(almuten.almuten) == 1 else None
    temperament = build_temperament(chart, planets, houses, reports, almuten_name)
    behaviour = build_behaviour_ruler(planets, houses, reports)
    behaviour.evidence.append(
        "temperament filter: " + (", ".join(temperament.dominant) or "unresolved")
    )
    syzygy = next(row.longitude for row in almuten.rows if row.name == "Syzygy")

    return NatalTechnicalReport(
        solar=solar,
        day_ruler=day_ruler,
        hour_ruler=hour_ruler,
        almuten=almuten,
        lots=lots,
        duads=_duads(planets, houses, lots),
        houses=_house_structure(planets, houses),
        temperament=temperament,
        primary_motivation=build_primary_motivation(planets, houses, reports),
        behaviour=behaviour,
        geniture=build_geniture_factors(reports),
        mind=build_mind_factors(chart, reports),
        syzygy_longitude=syzygy,
    )
