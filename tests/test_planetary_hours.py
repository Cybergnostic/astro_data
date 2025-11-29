from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

import swisseph as swe

from hor_tools.almuten import _sunrise_sunset, planetary_day_hour_rulers, planetary_hour_from_local
from hor_tools.models import ChartInput

SOLAR_DATA = {
    "birth_time": "17:32:36",
    "sunrise": "05:29:37",
    "sunset": "18:26:04",
}

NIS_LAT = 43 + 19 / 60.0
NIS_LON = 21 + 54 / 60.0


class PlanetaryHoursTest(unittest.TestCase):
    def _jd_to_local(self, jd: float, tz_offset_hours: float) -> datetime:
        year, month, day, ut_hour = swe.revjul(jd, swe.GREG_CAL)
        hour = int(ut_hour)
        minute_float = (ut_hour - hour) * 60
        minute = int(minute_float)
        second = int(round((minute_float - minute) * 60))
        if second == 60:
            second = 0
            minute += 1
        if minute == 60:
            minute = 0
            hour += 1
        dt_utc = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
        return dt_utc + timedelta(hours=tz_offset_hours)

    def test_morinus_planetary_hour_matches(self) -> None:
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
        self.assertEqual("Venus", day_ruler)
        self.assertEqual("Jupiter", hour_ruler)

        local_midnight = dt_local.replace(hour=0, minute=0, second=0, microsecond=0)
        utc_midnight = local_midnight - timedelta(hours=tz_offset_hours)
        base_jd = swe.julday(
            utc_midnight.year,
            utc_midnight.month,
            utc_midnight.day,
            utc_midnight.hour + utc_midnight.minute / 60.0 + utc_midnight.second / 3600.0,
            swe.GREG_CAL,
        )

        sunrise_ut, sunset_ut = _sunrise_sunset(base_jd, chart.latitude, chart.longitude)
        sunrise_local = self._jd_to_local(sunrise_ut, tz_offset_hours)
        sunset_local = self._jd_to_local(sunset_ut, tz_offset_hours)

        expected_sunrise = datetime.combine(
            local_midnight.date(),
            datetime.strptime(SOLAR_DATA["sunrise"], "%H:%M:%S").time(),
        )
        expected_sunset = datetime.combine(
            local_midnight.date(),
            datetime.strptime(SOLAR_DATA["sunset"], "%H:%M:%S").time(),
        )

        self.assertLess(abs((sunrise_local - expected_sunrise).total_seconds()), 90)
        self.assertLess(abs((sunset_local - expected_sunset).total_seconds()), 90)

        self.assertEqual(
            "Jupiter",
            planetary_hour_from_local(
                SOLAR_DATA["birth_time"],
                SOLAR_DATA["sunrise"],
                SOLAR_DATA["sunset"],
                "Venus",
            ),
        )


if __name__ == "__main__":
    unittest.main()
