from __future__ import annotations

from pathlib import Path

import pytest

from hor_tools.analysis.lots import _father_uses_jupiter, build_lots
from hor_tools.hor_parser import load_hor
from hor_tools.models import Houses, PlanetPosition


FIXTURE = Path(__file__).parent / "fixtures" / "sample_nis.hor"


def _planet(name: str, longitude: float) -> PlanetPosition:
    return PlanetPosition(
        name=name,
        longitude=longitude,
        latitude=0.0,
        speed_long=0.0,
        speed_lat=0.0,
        house=int(longitude // 30.0) + 1,
        retrograde=False,
    )


def _synthetic_chart_bodies() -> tuple[list[PlanetPosition], Houses]:
    planets = [
        _planet("Sun", 0.0),
        _planet("Moon", 20.0),
        _planet("Mercury", 30.0),
        _planet("Venus", 40.0),
        _planet("Mars", 60.0),
        _planet("Jupiter", 80.0),
        _planet("Saturn", 100.0),
    ]
    houses = Houses(
        cusps=[0.0] + [float(index * 30) for index in range(12)],
        asc=0.0,
        mc=270.0,
    )
    return planets, houses


def test_morinus_fixture_preserves_native_sex() -> None:
    chart = load_hor(FIXTURE)
    assert chart.male is True


@pytest.mark.parametrize("is_day", [True, False])
def test_hermes_marriage_lot_is_sex_specific_but_not_sect_reversed(
    is_day: bool,
) -> None:
    planets, houses = _synthetic_chart_bodies()

    male = build_lots(planets, houses, is_day, native_male=True)
    male_lot = next(lot for lot in male.topical if lot.name == "Marriage (Hermes — male)")
    assert male_lot.longitude == pytest.approx(300.0)
    assert male_lot.formula.startswith("Asc + Venus - Saturn")

    female = build_lots(planets, houses, is_day, native_male=False)
    female_lot = next(lot for lot in female.topical if lot.name == "Marriage (Hermes — female)")
    assert female_lot.longitude == pytest.approx(60.0)
    assert female_lot.formula.startswith("Asc + Saturn - Venus")


def test_father_lot_jupiter_substitution_solar_boundaries() -> None:
    # Cazimi is not combustion.
    assert _father_uses_jupiter(0.1, 0.0) is False

    # Combust Saturn is replaced on either side of the Sun.
    assert _father_uses_jupiter(5.0, 0.0) is True
    assert _father_uses_jupiter(355.0, 0.0) is True

    # Under beams on the occidental return side is entering combustion.
    assert _father_uses_jupiter(10.0, 0.0) is True

    # The same elongation on the oriental side is leaving the Sun, so Saturn remains.
    assert _father_uses_jupiter(350.0, 0.0) is False

    # Outside the beams Saturn remains the Father-Lot significator.
    assert _father_uses_jupiter(20.0, 0.0) is False
