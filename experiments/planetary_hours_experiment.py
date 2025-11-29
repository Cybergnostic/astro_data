"""Quick experiment to mirror the Morinus planetary hour example."""

from datetime import datetime, timedelta, timezone

import swisseph as swe

from hor_tools.almuten import _sunrise_sunset, planetary_day_hour_rulers, planetary_hour_from_local
from hor_tools.astro_engine import julian_day_from_chart
from hor_tools.models import ChartInput

NIS_LAT = 43 + 19 / 60.0
NIS_LON = 21 + 54 / 60.0


def main() -> None:
    tz_offset_hours = 2.0  # CET + DST
    dt_local = datetime(1996, 9, 6, 17, 32, 36)
    dt_utc = (dt_local - timedelta(hours=tz_offset_hours)).replace(tzinfo=timezone.utc)

    chart = ChartInput(
        name="Morinus example",
        datetime_utc=dt_utc,
        tz_offset_hours=tz_offset_hours,
        latitude=NIS_LAT,
        longitude=NIS_LON,
        house_system="W",
        zodiac="T",
    )

    day_ruler, hour_ruler = planetary_day_hour_rulers(chart)
    print("day_ruler:", day_ruler, "hour_ruler:", hour_ruler)

    # For comparison: local helper using Morinus sunrise/sunset strings
    print(
        "local helper:",
        planetary_hour_from_local("17:32:36", "05:29:37", "18:26:04", "Venus"),
    )

    # Also show the UT sunrise/sunset used internally and their local equivalents.
    jd_birth = julian_day_from_chart(chart)
    local_midnight = dt_local.replace(hour=0, minute=0, second=0, microsecond=0)
    utc_midnight = local_midnight - timedelta(hours=tz_offset_hours)
    base_jd = swe.julday(
        utc_midnight.year,
        utc_midnight.month,
        utc_midnight.day,
        utc_midnight.hour + utc_midnight.minute / 60.0 + utc_midnight.second / 3600.0,
        swe.GREG_CAL,
    )
    sunrise_ut, sunset_ut = _sunrise_sunset(base_jd, chart.latitude, chart.longitude, chart.tz_offset_hours)
    print("birth_jd UT:", jd_birth)
    print("sunrise UT JD:", sunrise_ut, "sunset UT JD:", sunset_ut)


if __name__ == "__main__":
    main()
