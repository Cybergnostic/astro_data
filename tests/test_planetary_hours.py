from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

import swisseph as swe

from hor_tools.almuten import _sunrise_sunset, planetary_day_hour_rulers, planetary_hour_from_local
from hor_tools.models import ChartInput

NIS_LAT = 43 + 19 / 60.0
NIS_LON = 21 + 54 / 60.0


class PlanetaryHoursTest(unittest.TestCase):
    def _jd_to_local(self, jd: float, tz_offset_hours: float) -> datetime:
        year, month, day, ut_hour = swe.revjul(jd, swe.GREG_CAL)
        dt_utc = datetime(year, month, day, tzinfo=timezone.utc) + timedelta(hours=ut_hour)
        return dt_utc + timedelta(hours=tz_offset_hours)

    def _chart(self) -> ChartInput:
        tz_offset_hours = 2.0
        dt_local = datetime(1996, 9, 6, 17, 32, 36)
        dt_utc = (dt_local - timedelta(hours=tz_offset_hours)).replace(tzinfo=timezone.utc)
        return ChartInput(
            name="geographic planetary hour example",
            datetime_utc=dt_utc,
            tz_offset_hours=tz_offset_hours,
            latitude=NIS_LAT,
            longitude=NIS_LON,
            house_system="W",
            zodiac="T",
        )

    def test_planetary_hour_uses_geographic_sunrise(self) -> None:
        chart = self._chart()
        day_ruler, hour_ruler = planetary_day_hour_rulers(chart)
        self.assertEqual("Venus", day_ruler)
        self.assertEqual("Saturn", hour_ruler)

        dt_local = chart.datetime_utc.astimezone(timezone.utc).replace(tzinfo=None) + timedelta(hours=2)
        local_midnight = dt_local.replace(hour=0, minute=0, second=0, microsecond=0)
        utc_midnight = local_midnight - timedelta(hours=2)
        base_jd = swe.julday(
            utc_midnight.year,
            utc_midnight.month,
            utc_midnight.day,
            utc_midnight.hour,
            swe.GREG_CAL,
        )

        sunrise_ut, sunset_ut = _sunrise_sunset(base_jd, NIS_LAT, NIS_LON, 2.0)
        sunrise_local = self._jd_to_local(sunrise_ut, 2.0)
        sunset_local = self._jd_to_local(sunset_ut, 2.0)

        expected_sunrise = datetime(1996, 9, 6, 6, 3, tzinfo=timezone.utc)
        expected_sunset = datetime(1996, 9, 6, 18, 57, tzinfo=timezone.utc)
        self.assertLess(abs((sunrise_local - expected_sunrise).total_seconds()), 120)
        self.assertLess(abs((sunset_local - expected_sunset).total_seconds()), 120)

        self.assertEqual(
            "Saturn",
            planetary_hour_from_local("17:32:36", "06:03:13", "18:57:17", "Venus"),
        )

    def test_timezone_offset_does_not_replace_longitude(self) -> None:
        chart = self._chart()
        dt_local = chart.datetime_utc.astimezone(timezone.utc).replace(tzinfo=None) + timedelta(hours=2)
        utc_midnight = dt_local.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(hours=2)
        base_jd = swe.julday(utc_midnight.year, utc_midnight.month, utc_midnight.day, utc_midnight.hour, swe.GREG_CAL)

        sunrise_a, sunset_a = _sunrise_sunset(base_jd, NIS_LAT, NIS_LON, 1.0)
        sunrise_b, sunset_b = _sunrise_sunset(base_jd, NIS_LAT, NIS_LON, 2.0)
        self.assertAlmostEqual(sunrise_a, sunrise_b, places=9)
        self.assertAlmostEqual(sunset_a, sunset_b, places=9)

        zone_meridian_sunrise, _ = _sunrise_sunset(base_jd, NIS_LAT, 30.0, 2.0)
        self.assertGreater(abs(zone_meridian_sunrise - sunrise_a) * 24 * 60, 20)


if __name__ == "__main__":
    unittest.main()
