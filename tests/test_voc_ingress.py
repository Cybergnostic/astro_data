from datetime import datetime, timezone
from unittest.mock import patch

import swisseph as swe

from hor_tools.analysis.conditions import moon_void_of_course
from hor_tools.models import ChartInput, PlanetPosition


def chart() -> ChartInput:
    return ChartInput(
        name="voc-ingress",
        datetime_utc=datetime(2000, 1, 1, tzinfo=timezone.utc),
        tz_offset_hours=0.0,
        latitude=0.0,
        longitude=0.0,
        house_system="W",
        zodiac="T",
    )


def moon() -> PlanetPosition:
    return PlanetPosition(
        name="Moon",
        longitude=29.9,
        latitude=0.0,
        speed_long=9.6,
        speed_lat=0.0,
        house=1,
        retrograde=False,
    )


def fake_longitude_factory(sun_longitude: float):
    fixed = {
        swe.SUN: sun_longitude,
        swe.MERCURY: 45.0,
        swe.VENUS: 76.0,
        swe.MARS: 107.0,
        swe.JUPITER: 153.0,
        swe.SATURN: 217.0,
    }

    def fake(jd: float, body_id: int) -> float:
        if body_id == swe.MOON:
            # 29.9 -> 30.1 during one 30-minute step; ingress is halfway.
            return (29.9 + 9.6 * jd) % 360.0
        return fixed[body_id]

    return fake


def test_aspect_before_ingress_inside_final_step_defeats_voc() -> None:
    # Sun at 29.95: Moon perfects conjunction one quarter of the way through
    # the final 30-minute step, before entering Taurus halfway through.
    with (
        patch("hor_tools.analysis.conditions.ensure_ephe_path"),
        patch("hor_tools.analysis.conditions.julian_day_from_chart", return_value=0.0),
        patch(
            "hor_tools.analysis.conditions._planet_longitude",
            side_effect=fake_longitude_factory(29.95),
        ),
    ):
        assert moon_void_of_course(chart(), moon(), step_hours=0.5) is False


def test_no_aspect_before_ingress_remains_void() -> None:
    # Sun at 29.7 is already behind the Moon, so no conjunction perfects before
    # the same sign ingress; the other synthetic bodies avoid exact major rays.
    with (
        patch("hor_tools.analysis.conditions.ensure_ephe_path"),
        patch("hor_tools.analysis.conditions.julian_day_from_chart", return_value=0.0),
        patch(
            "hor_tools.analysis.conditions._planet_longitude",
            side_effect=fake_longitude_factory(29.7),
        ),
    ):
        assert moon_void_of_course(chart(), moon(), step_hours=0.5) is True
