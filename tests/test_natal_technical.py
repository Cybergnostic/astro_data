from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from hor_tools import astro_engine
from hor_tools.analysis import build_reports
from hor_tools.analysis.duads import dodekatemorion_longitude
from hor_tools.analysis.lots import _sees_by_sign
from hor_tools.analysis.repulsion import _debilities_of_host_at_guest
from hor_tools.analysis.stars import COURSE_FIRST_MAGNITUDE_PRIMARY_NATURE
from hor_tools.analysis.technical import build_natal_technical_report
from hor_tools.analysis.temperament import (
    DUAD_CONTACT_ORB,
    _planet_qualities,
    _primary_nature_qualities,
    _qualities_to_scores,
)
from hor_tools.hor_parser import load_hor


FIXTURE = Path(__file__).parent / "fixtures" / "sample_nis.hor"


def _fixture_report(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(astro_engine, "EPHE_PATH", str(tmp_path))
    chart = load_hor(FIXTURE)
    planets = astro_engine.compute_planets(chart)
    houses = astro_engine.compute_houses(chart)
    reports, relationships = build_reports(chart, planets, houses)
    technical = build_natal_technical_report(
        chart, planets, houses, reports, relationships
    )
    return chart, planets, houses, reports, technical


def test_course_duad_examples() -> None:
    saturn = 180 + 9 + 24 / 60
    mars = 210 + 20 + 17 / 60
    assert dodekatemorion_longitude(saturn) == pytest.approx(
        270 + 22 + 48 / 60, abs=1e-9
    )
    assert dodekatemorion_longitude(mars) == pytest.approx(
        90 + 3 + 24 / 60, abs=1e-9
    )
    assert DUAD_CONTACT_ORB == 5.0


def test_partial_planetary_quality_is_not_forced_into_one_temperament() -> None:
    assert _qualities_to_scores({"dry"}) == {"K": 1, "S": 0, "M": 1, "F": 0}
    assert _qualities_to_scores({"moist"}) == {"K": 0, "S": 1, "M": 0, "F": 1}
    assert _qualities_to_scores({"hot", "dry"}) == {"K": 1, "S": 0, "M": 0, "F": 0}


def test_teacher_temperament_keeps_superior_natures_fixed() -> None:
    for name, expected in (
        ("Saturn", {"cold", "dry"}),
        ("Jupiter", {"hot", "moist"}),
        ("Mars", {"hot", "dry"}),
    ):
        oriental = SimpleNamespace(planet=SimpleNamespace(name=name), oriental=True)
        occidental = SimpleNamespace(planet=SimpleNamespace(name=name), oriental=False)
        assert _planet_qualities(oriental) == expected
        assert _planet_qualities(occidental) == expected

    venus_oriental = SimpleNamespace(planet=SimpleNamespace(name="Venus"), oriental=True)
    venus_occidental = SimpleNamespace(planet=SimpleNamespace(name="Venus"), oriental=False)
    mercury_oriental = SimpleNamespace(planet=SimpleNamespace(name="Mercury"), oriental=True)
    mercury_occidental = SimpleNamespace(planet=SimpleNamespace(name="Mercury"), oriental=False)
    assert _planet_qualities(venus_oriental) == {"hot", "moist"}
    assert _planet_qualities(venus_occidental) == {"cold", "moist"}
    assert _planet_qualities(mercury_oriental) == {"hot", "moist"}
    assert _planet_qualities(mercury_occidental) == {"cold", "dry"}


def test_course_first_magnitude_stars_use_primary_planet_nature() -> None:
    assert COURSE_FIRST_MAGNITUDE_PRIMARY_NATURE["Aldebaran"] == "Mars"
    assert COURSE_FIRST_MAGNITUDE_PRIMARY_NATURE["Regulus"] == "Mars"
    assert COURSE_FIRST_MAGNITUDE_PRIMARY_NATURE["Spica"] == "Venus"
    assert COURSE_FIRST_MAGNITUDE_PRIMARY_NATURE["Sirius"] == "Jupiter"
    assert COURSE_FIRST_MAGNITUDE_PRIMARY_NATURE["Canopus"] == "Saturn"
    assert _qualities_to_scores(_primary_nature_qualities("Mars")) == {
        "K": 1,
        "S": 0,
        "M": 0,
        "F": 0,
    }
    assert _qualities_to_scores(_primary_nature_qualities("Venus")) == {
        "K": 0,
        "S": 0,
        "M": 0,
        "F": 1,
    }


def test_lot_ruler_sight_is_sign_based_not_degree_orb_based() -> None:
    assert _sees_by_sign(1.0, 28.0) is True
    assert _sees_by_sign(1.0, 61.0) is True
    assert _sees_by_sign(1.0, 151.0) is False


def test_repulsion_uses_host_detriment_or_fall() -> None:
    assert _debilities_of_host_at_guest("Moon", 270.0) == ["detriment"]
    assert _debilities_of_host_at_guest("Saturn", 0.0) == ["fall"]


def test_reference_chart_uses_apparent_day_frame_and_teacher_planetary_hour(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _chart, _planets, _houses, _reports, technical = _fixture_report(monkeypatch, tmp_path)
    assert technical.solar.is_day is True
    assert technical.day_ruler == "Mercury"
    assert technical.hour_ruler == "Mars"
    assert technical.almuten.accidental.day_ruler == technical.day_ruler
    assert technical.almuten.accidental.hour_ruler == technical.hour_ruler


def test_reference_chart_lots_preserve_both_eros_variants(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _chart, _planets, _houses, _reports, technical = _fixture_report(monkeypatch, tmp_path)
    fortune = next(lot for lot in technical.lots.hermetic if lot.name == "Fortune")
    assert fortune.longitude == pytest.approx(150 + 26 + 46 / 60 + 26 / 3600, abs=0.05)

    hermetic = next(lot for lot in technical.lots.hermetic if lot.name == "Eros (Hermetic)")
    topical = next(
        lot
        for lot in technical.lots.topical
        if lot.name == "Eros (relationship-course variant)"
    )
    assert hermetic.formula != topical.formula
    assert hermetic.longitude != pytest.approx(topical.longitude, abs=1e-8)


def test_reference_chart_behaviour_ruler_uses_mercury_moon_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _chart, _planets, _houses, _reports, technical = _fixture_report(monkeypatch, tmp_path)
    assert technical.behaviour.primary == "Venus"
    assert "conjunct Mercury" in technical.behaviour.evidence[0]


def test_reference_chart_preserves_specific_primary_motivation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _chart, _planets, _houses, _reports, technical = _fixture_report(monkeypatch, tmp_path)
    asc = technical.primary_motivation.factors[0]
    asc_ruler = technical.primary_motivation.factors[1]
    assert asc.motivation == "power through energetic exchange and interaction with others"
    assert asc_ruler.motivation == "accumulation and preservation of material values"
    assert "in aversion to Ascendant sign" in asc_ruler.condition


def test_reference_chart_exposes_human_judgment_sections_without_fake_winners(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _chart, _planets, _houses, _reports, technical = _fixture_report(monkeypatch, tmp_path)
    assert technical.primary_motivation.factors
    assert technical.geniture.candidates
    assert technical.mind.mercury_almuten.winners
    assert technical.mind.moon_almuten.winners
    assert not hasattr(technical, "fortune_adversity")


def test_temperament_report_is_auditable_row_by_row(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _chart, _planets, _houses, _reports, technical = _fixture_report(monkeypatch, tmp_path)
    factors = [row.factor for row in technical.temperament.rows]
    assert factors == [
        "ASC",
        "ASC ruler nature",
        "ASC ruler sign",
        "Aspects to ASC ruler",
        "Planets and nodes in House I",
        "Planetary duads / 1st-mag stars on ASC",
        "Aspects to ASC",
        "Lunar phase",
        "Moon sign",
        "Moon dispositor sign",
        "Moon aspects",
        "Season",
        "Almuten Figuris nature",
        "Almuten Figuris sign",
    ]
    assert set(technical.temperament.totals) == {"K", "S", "M", "F"}
    assert sum(technical.temperament.totals.values()) > 0
