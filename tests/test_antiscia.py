import pytest

from hor_tools.analysis.antiscia import (
    antiscia_longitude,
    contra_antiscia_longitude,
    reflection_hits_for_planet,
)
from hor_tools.models import PlanetPosition


def make_planet(name: str, longitude: float, speed: float = 1.0) -> PlanetPosition:
    return PlanetPosition(
        name=name,
        longitude=longitude,
        latitude=0.0,
        speed_long=speed,
        speed_lat=0.0,
        house=1,
        retrograde=False,
    )


def test_reflection_math_examples():
    # Reflection across solstice axis
    assert antiscia_longitude(88.0) == pytest.approx(92.0)  # 28° Gemini -> Cancer
    # Reflection across equinox axis
    assert contra_antiscia_longitude(350.0) == pytest.approx(10.0)  # 20° Pisces -> 10° Aries


def test_degree_sum_rule_no_orb():
    # Mercury 28° Gemini (88°) antiscia sign = Cancer; degree int=28 → needs partner at degree 1 (28+1=29)
    mercury = make_planet("Mercury", 88.0)
    moon_exact = make_planet("Moon", 91.0)  # 1° Cancer -> should count
    moon_off = make_planet("MoonOff", 92.0)  # 2° Cancer -> should NOT count

    hits, _ = reflection_hits_for_planet(mercury, [mercury, moon_exact, moon_off])
    assert [h.other for h in hits] == ["Moon"]
    assert hits[0].target_longitude == pytest.approx(antiscia_longitude(88.0))


def test_minutes_can_cross_over_when_degree_sum_matches():
    # 28°59' Gemini (88.9833) -> requires partner with degree int 1 in Cancer, minutes may differ
    mercury = make_planet("Mercury", 88.9833)
    moon_fuzzy = make_planet("Moon", 91.0166)  # 1°01' Cancer

    hits, _ = reflection_hits_for_planet(mercury, [mercury, moon_fuzzy])
    assert len(hits) == 1
    assert hits[0].other == "Moon"
    # Orb is informational only; should be small here
    assert hits[0].orb < 0.05
