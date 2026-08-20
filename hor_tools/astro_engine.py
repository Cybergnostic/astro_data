"""Swiss Ephemeris wrapper and Whole sign house calculations."""

from __future__ import annotations

import os
from datetime import timezone
import swisseph as swe

from .models import ChartInput, Houses, PlanetPosition
from .synodic import (
    compute_elongation_and_orientation,
    compute_inferior_synodic_phase,
    compute_lunar_synodic_phase,
    compute_superior_synodic_phase,
)

EPHE_PATH = os.environ.get("SWISSEPH_EPHE")
PLANETS: list[tuple[str, int]] = [
    ("Sun", swe.SUN),
    ("Moon", swe.MOON),
    ("Mercury", swe.MERCURY),
    ("Venus", swe.VENUS),
    ("Mars", swe.MARS),
    ("Jupiter", swe.JUPITER),
    ("Saturn", swe.SATURN),
]
FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED
_STATION_PLANETS = {swe.MERCURY, swe.VENUS, swe.MARS, swe.JUPITER, swe.SATURN}


def set_ephe_path(path: str) -> None:
    """Override the ephemeris directory used for all Swiss Ephemeris calls."""
    global EPHE_PATH
    EPHE_PATH = path


def ensure_ephe_path() -> str:
    """Resolve and activate the Swiss Ephemeris path."""
    path = EPHE_PATH or os.environ.get("SWISSEPH_EPHE")
    if not path:
        raise RuntimeError(
            "Swiss Ephemeris path is not set. Set SWISSEPH_EPHE or pass --ephe to hor-reader."
        )
    swe.set_ephe_path(path)
    return path


def _station_phase_near(jd_ut: float, planet_id: int) -> str | None:
    """Detect a first/second station from the motion trend around the chart day.

    The course instructs the student to inspect adjacent ephemeris days rather
    than use one universal absolute-speed cutoff.  We therefore compare signed
    longitudinal motion one day before and one day after the chart moment:
    direct -> retrograde is the first station; retrograde -> direct the second.
    """
    if planet_id not in _STATION_PLANETS:
        return None

    _lon, _lat, past_speed, _lat_speed = _planet_position(jd_ut - 1.0, planet_id)
    _lon, _lat, future_speed, _lat_speed = _planet_position(jd_ut + 1.0, planet_id)

    if past_speed > 0.0 and future_speed < 0.0:
        return "first"
    if past_speed < 0.0 and future_speed > 0.0:
        return "second"
    return None


def compute_planets(chart: ChartInput) -> list[PlanetPosition]:
    """Calculate planetary positions, motion trends and Whole sign houses."""
    ensure_ephe_path()
    jd_ut = julian_day_from_chart(chart)
    asc_longitude, _ = _ascendant_and_mc(jd_ut, chart.latitude, chart.longitude)
    asc_sign = int(asc_longitude // 30)

    positions: list[PlanetPosition] = []
    for name, swe_id in PLANETS:
        lon, lat, sp_lon, sp_lat = _planet_position(jd_ut, swe_id)
        house = _house_for_longitude(lon, asc_sign)
        retrograde = sp_lon < 0
        positions.append(
            PlanetPosition(
                name=name,
                longitude=lon,
                latitude=lat,
                speed_long=sp_lon,
                speed_lat=sp_lat,
                house=house,
                retrograde=retrograde,
                station=_station_phase_near(jd_ut, swe_id),
            )
        )

    # Post-process synodic data once Sun longitude is known.
    sun = next(p for p in positions if p.name == "Sun")
    for planet in positions:
        elong, _, _ = compute_elongation_and_orientation(planet.longitude, sun.longitude)
        planet.elongation_from_sun = elong
        if planet.name in {"Saturn", "Jupiter", "Mars"}:
            planet.synodic_phase = compute_superior_synodic_phase(planet, sun.longitude)
        elif planet.name in {"Venus", "Mercury"}:
            planet.synodic_phase = compute_inferior_synodic_phase(planet, sun.longitude)
        elif planet.name == "Moon":
            planet.synodic_phase = compute_lunar_synodic_phase(planet, sun.longitude)
        else:
            planet.synodic_phase = None
    return positions


def compute_houses(chart: ChartInput) -> Houses:
    """Compute Ascendant/MC and derive Whole sign cusps."""
    ensure_ephe_path()
    jd_ut = julian_day_from_chart(chart)
    asc_longitude, mc_longitude = _ascendant_and_mc(jd_ut, chart.latitude, chart.longitude)
    asc_sign = int(asc_longitude // 30)

    cusps = [0.0]
    for house in range(12):
        cusps.append((asc_sign * 30.0 + house * 30.0) % 360.0)

    return Houses(cusps=cusps, asc=asc_longitude, mc=mc_longitude)


def julian_day_from_chart(chart: ChartInput) -> float:
    """Convert the chart's datetime into a Julian day (UT frame)."""
    dt_utc = chart.datetime_utc
    if dt_utc.tzinfo is not None:
        dt_utc = dt_utc.astimezone(timezone.utc).replace(tzinfo=None)

    ut_hour = (
        dt_utc.hour
        + dt_utc.minute / 60.0
        + dt_utc.second / 3600.0
        + dt_utc.microsecond / 3_600_000_000.0
    )
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, ut_hour, swe.GREG_CAL)


def _planet_position(jd_ut: float, planet_id: int) -> tuple[float, float, float, float]:
    """Return ecliptic longitude/latitude and daily speeds for a planet."""
    result = swe.calc_ut(jd_ut, planet_id, FLAGS)
    if len(result) == 2 and isinstance(result[0], (tuple, list)):
        position = result[0]
    else:
        position = result
    lon = float(position[0])
    lat = float(position[1])
    speed_long = float(position[3])
    speed_lat = float(position[4])
    return lon, lat, speed_long, speed_lat


def _ascendant_and_mc(jd_ut: float, latitude: float, longitude: float) -> tuple[float, float | None]:
    """Compute Ascendant and MC using Swiss Ephemeris housing (Placidus for angles)."""
    cusps, ascmc = swe.houses_ex(jd_ut, latitude, longitude, b"P")
    asc = float(ascmc[0])
    mc = float(ascmc[1]) if len(ascmc) > 1 else None
    return asc, mc


def _house_for_longitude(longitude: float, asc_sign: int) -> int:
    """Return the Whole sign house number for a given ecliptic longitude."""
    planet_sign = int(longitude // 30)
    return ((planet_sign - asc_sign) % 12) + 1
