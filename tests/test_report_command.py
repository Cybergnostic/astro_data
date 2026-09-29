from datetime import date, time, timezone

import pytest

from hor_tools.commands.report import build_chart


def test_build_chart_from_normalized_local_data() -> None:
    chart = build_chart(
        name="Hint client",
        local_date=date(1988, 6, 8),
        local_time=time(19, 20),
        timezone_name="Europe/Belgrade",
        latitude=43.316667,
        longitude=21.9,
        location_name="Nish, Yugoslavia",
        sex="unknown",
    )
    assert chart.name == "Hint client"
    assert chart.datetime_utc.tzinfo == timezone.utc
    assert chart.datetime_utc.hour == 17
    assert chart.datetime_utc.minute == 20
    assert chart.tz_offset_hours == 2.0
    assert chart.house_system == "W"
    assert chart.zodiac == "T"
    assert chart.male is None


def test_build_chart_rejects_dst_transition_ambiguity() -> None:
    with pytest.raises(ValueError, match="timezone transition"):
        build_chart(
            name="Ambiguous",
            local_date=date(2026, 10, 25),
            local_time=time(2, 30),
            timezone_name="Europe/Belgrade",
            latitude=44.8,
            longitude=20.47,
            location_name="Belgrade",
            sex="unknown",
        )
