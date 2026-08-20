from __future__ import annotations

from pathlib import Path

import pytest

from hor_tools import astro_engine
from hor_tools.hor_parser import load_hor


FIXTURE = Path(__file__).parent / "fixtures" / "sample_nis.hor"

# Positions from the reference Morinus table for this fixture.  The fixture name
# is anonymized, but its date/time/location fields intentionally match the
# reference chart used during the calculation audit.
EXPECTED_LONGITUDES = {
    "Saturn": 270 + 6 / 60 + 28 / 3600,
    "Jupiter": 30 + 21 + 16 / 60 + 23 / 3600,
    "Mars": 330 + 10 + 51 / 60 + 32 / 3600,
    "Sun": 60 + 18 + 6 / 60 + 33 / 3600,
    "Venus": 60 + 24 + 49 / 60 + 59 / 3600,
    "Mercury": 60 + 24 + 44 / 60 + 19 / 3600,
    "Moon": 7 + 5 / 60 + 12 / 3600,
}

EXPECTED_HOUSES = {
    "Saturn": 2,
    "Jupiter": 6,
    "Mars": 4,
    "Sun": 7,
    "Venus": 7,
    "Mercury": 7,
    "Moon": 5,
}

EXPECTED_ASC = 240 + 7 + 47 / 60 + 47 / 3600


def test_real_morinus_fixture_reproduces_reference_positions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # An empty real directory lets pyswisseph use its Moshier fallback in CI.
    monkeypatch.setattr(astro_engine, "EPHE_PATH", str(tmp_path))

    chart = load_hor(FIXTURE)
    planets = astro_engine.compute_planets(chart)
    houses = astro_engine.compute_houses(chart)
    by_name = {planet.name: planet for planet in planets}

    for name, expected_longitude in EXPECTED_LONGITUDES.items():
        assert by_name[name].longitude == pytest.approx(expected_longitude, abs=0.03)
        assert by_name[name].house == EXPECTED_HOUSES[name]

    assert houses.asc == pytest.approx(EXPECTED_ASC, abs=0.03)
