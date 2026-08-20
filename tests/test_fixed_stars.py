from datetime import datetime, timezone
from unittest.mock import patch

from hor_tools.analysis.stars import BRIGHT_STARS, stars_near_longitude
from hor_tools.models import ChartInput


def chart() -> ChartInput:
    return ChartInput(
        name="stars",
        datetime_utc=datetime(2000, 1, 1, tzinfo=timezone.utc),
        tz_offset_hours=0.0,
        latitude=0.0,
        longitude=0.0,
        house_system="W",
        zodiac="T",
    )


def test_course_catalogue_is_not_old_eleven_star_subset() -> None:
    for name in ("Algol", "Arcturus", "Achernar", "Acrux", "Alnilam", "Scheat"):
        assert name in BRIGHT_STARS
    assert len(BRIGHT_STARS) > 80


def test_unresolved_star_does_not_erase_later_valid_hits() -> None:
    with (
        patch("hor_tools.analysis.stars.julian_day_from_chart", return_value=2451545.0),
        patch("hor_tools.analysis.stars.ensure_ephe_path"),
        patch(
            "hor_tools.analysis.stars.COURSE_STARS",
            [("Missing", ("Missing",)), ("Valid", ("Valid",))],
        ),
        patch(
            "hor_tools.analysis.stars._resolve_star",
            side_effect=[None, ((100.2, 3.5, 0.0, 0.0, 0.0, 0.0), 1.0)],
        ),
    ):
        hits = stars_near_longitude(chart(), 100.0, body_latitude=1.0)

    assert hits == ["Valid (Δlat 2.50°)"]
