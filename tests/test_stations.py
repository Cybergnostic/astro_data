from unittest.mock import patch

import swisseph as swe

from hor_tools.astro_engine import _station_phase_near
from hor_tools.models import PlanetPosition
from hor_tools.synodic import compute_inferior_synodic_phase, compute_superior_synodic_phase


def fake_position_with_speeds(past: float, future: float):
    def fake(jd: float, planet_id: int):
        speed = past if jd < 0.0 else future
        return 0.0, 0.0, speed, 0.0
    return fake


def planet(name: str, longitude: float, speed: float, station: str | None) -> PlanetPosition:
    return PlanetPosition(
        name=name,
        longitude=longitude,
        latitude=0.0,
        speed_long=speed,
        speed_lat=0.0,
        house=1,
        retrograde=speed < 0,
        station=station,
    )


def test_first_station_detected_from_direct_to_retrograde_reversal() -> None:
    with patch(
        "hor_tools.astro_engine._planet_position",
        side_effect=fake_position_with_speeds(0.05, -0.05),
    ):
        assert _station_phase_near(0.0, swe.JUPITER) == "first"


def test_second_station_detected_from_retrograde_to_direct_reversal() -> None:
    with patch(
        "hor_tools.astro_engine._planet_position",
        side_effect=fake_position_with_speeds(-0.05, 0.05),
    ):
        assert _station_phase_near(0.0, swe.JUPITER) == "second"


def test_no_station_without_signed_reversal() -> None:
    with patch(
        "hor_tools.astro_engine._planet_position",
        side_effect=fake_position_with_speeds(0.05, 0.02),
    ):
        assert _station_phase_near(0.0, swe.JUPITER) is None


def test_synodic_phase_uses_station_trend_even_with_nonzero_current_speed() -> None:
    superior = planet("Saturn", 340.0, 0.01, "first")
    inferior = planet("Mercury", 20.0, 0.02, "first")
    assert compute_superior_synodic_phase(superior, 0.0).code == "first_station"
    assert compute_inferior_synodic_phase(inferior, 0.0).code == "first_station_west"
