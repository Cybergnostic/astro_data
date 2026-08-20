"""Shared solar-horizon and planetary-hour calculations.

Sect is defined from apparent local sunrise to apparent local sunset.  Swiss
Ephemeris' default rise/set calculation uses refraction and the solar limb;
we deliberately do not set ``BIT_DISC_CENTER`` here.  This keeps borderline
charts consistent with observed sunrise/sunset rather than a geometric
Sun-centre altitude test.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import swisseph as swe

from ..astro_engine import ensure_ephe_path, julian_day_from_chart
from ..models import ChartInput

CHALDEAN_ORDER = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]
DAY_RULERS = {
    0: "Moon",
    1: "Mars",
    2: "Mercury",
    3: "Jupiter",
    4: "Venus",
    5: "Saturn",
    6: "Sun",
}


@dataclass(frozen=True)
class SolarFrame:
    """Local solar frame used by sect and planetary hours."""

    is_day: bool
    sunrise_jd: float
    sunset_jd: float
    sunrise_local: datetime
    sunset_local: datetime
    sun_true_altitude: float
    method: str = "apparent_sunrise_sunset"


def _naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _jd_to_utc_datetime(jd: float) -> datetime:
    year, month, day, hours = swe.revjul(jd, swe.GREG_CAL)
    hour = int(hours)
    minute_float = (hours - hour) * 60.0
    minute = int(minute_float)
    second_float = (minute_float - minute) * 60.0
    second = int(round(second_float))
    if second >= 60:
        second = 0
        minute += 1
    if minute >= 60:
        minute = 0
        hour += 1
    if hour >= 24:
        base = datetime(year, month, day) + timedelta(days=1)
        return base.replace(hour=0, minute=minute, second=second, tzinfo=timezone.utc)
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


def _local_midnight_jd(chart: ChartInput, day_offset: int = 0) -> float:
    dt_utc = _naive_utc(chart.datetime_utc)
    dt_local = dt_utc + timedelta(hours=chart.tz_offset_hours, days=day_offset)
    local_midnight = dt_local.replace(hour=0, minute=0, second=0, microsecond=0)
    utc_midnight = local_midnight - timedelta(hours=chart.tz_offset_hours)
    return swe.julday(
        utc_midnight.year,
        utc_midnight.month,
        utc_midnight.day,
        utc_midnight.hour
        + utc_midnight.minute / 60.0
        + utc_midnight.second / 3600.0,
        swe.GREG_CAL,
    )


def rise_set_for_local_day(chart: ChartInput, day_offset: int = 0) -> tuple[float, float]:
    """Return apparent sunrise and sunset UT Julian days for a local date."""

    ensure_ephe_path()
    base_jd = _local_midnight_jd(chart, day_offset)
    geopos = (chart.longitude, chart.latitude, chart.altitude_m or 0.0)

    rise_flag, rise_tret = swe.rise_trans(
        base_jd,
        swe.SUN,
        rsmi=swe.CALC_RISE,
        geopos=geopos,
    )
    set_flag, set_tret = swe.rise_trans(
        base_jd,
        swe.SUN,
        rsmi=swe.CALC_SET,
        geopos=geopos,
    )
    if rise_flag < 0 or not rise_tret:
        raise RuntimeError(
            f"Swiss Ephemeris could not determine sunrise at {chart.latitude}, {chart.longitude}."
        )
    if set_flag < 0 or not set_tret:
        raise RuntimeError(
            f"Swiss Ephemeris could not determine sunset at {chart.latitude}, {chart.longitude}."
        )
    return float(rise_tret[0]), float(set_tret[0])


def _sun_true_altitude(chart: ChartInput) -> float:
    jd = julian_day_from_chart(chart)
    equ = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH | swe.FLG_EQUATORIAL)[0]
    ra, dec, distance = float(equ[0]), float(equ[1]), float(equ[2])
    true_alt, _apparent_alt = swe.azalt(
        jd,
        swe.EQU2HOR,
        (chart.longitude, chart.latitude, chart.altitude_m or 0.0),
        0.0,
        10.0,
        (ra, dec, distance),
    )[1:]
    return float(true_alt)


def solar_frame_for_chart(chart: ChartInput) -> SolarFrame:
    """Return the chart's apparent sunrise/sunset frame and sect state."""

    birth_jd = julian_day_from_chart(chart)
    sunrise_jd, sunset_jd = rise_set_for_local_day(chart)
    is_day = sunrise_jd <= birth_jd < sunset_jd

    offset = timedelta(hours=chart.tz_offset_hours)
    sunrise_local = (_jd_to_utc_datetime(sunrise_jd) + offset).replace(tzinfo=None)
    sunset_local = (_jd_to_utc_datetime(sunset_jd) + offset).replace(tzinfo=None)
    return SolarFrame(
        is_day=is_day,
        sunrise_jd=sunrise_jd,
        sunset_jd=sunset_jd,
        sunrise_local=sunrise_local,
        sunset_local=sunset_local,
        sun_true_altitude=_sun_true_altitude(chart),
    )


def planetary_day_hour_rulers(chart: ChartInput) -> tuple[str, str]:
    """Return planetary day/hour rulers using the same apparent solar frame."""

    birth_jd = julian_day_from_chart(chart)
    dt_utc = _naive_utc(chart.datetime_utc)
    dt_local = dt_utc + timedelta(hours=chart.tz_offset_hours)
    sunrise_today, sunset_today = rise_set_for_local_day(chart, 0)

    if sunrise_today <= birth_jd < sunset_today:
        planetary_weekday = dt_local.weekday()
        day_ruler = DAY_RULERS[planetary_weekday]
        hour_len = (sunset_today - sunrise_today) / 12.0
        hour_number = int((birth_jd - sunrise_today) / hour_len)
    elif birth_jd >= sunset_today:
        sunrise_next, _ = rise_set_for_local_day(chart, 1)
        planetary_weekday = dt_local.weekday()
        day_ruler = DAY_RULERS[planetary_weekday]
        hour_len = (sunrise_next - sunset_today) / 12.0
        hour_number = 12 + int((birth_jd - sunset_today) / hour_len)
    else:
        _, sunset_prev = rise_set_for_local_day(chart, -1)
        prev_local = dt_local - timedelta(days=1)
        planetary_weekday = prev_local.weekday()
        day_ruler = DAY_RULERS[planetary_weekday]
        hour_len = (sunrise_today - sunset_prev) / 12.0
        hour_number = 12 + int((birth_jd - sunset_prev) / hour_len)

    hour_number = max(0, min(hour_number, 23))
    start = CHALDEAN_ORDER.index(day_ruler)
    hour_ruler = CHALDEAN_ORDER[(start + hour_number) % len(CHALDEAN_ORDER)]
    return day_ruler, hour_ruler
