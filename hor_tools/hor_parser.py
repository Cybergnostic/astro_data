"""Parsing utilities for Morinus ``.hor`` horoscope files."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import ChartInput


class HorParseError(ValueError):
    """Raised when a Morinus horoscope file cannot be parsed safely."""


# Morinus ``chart.Time`` constants used by the file serialization.
_TIME_ZONE = 0
_TIME_GREENWICH = 1
_TIME_LOCAL_MEAN = 2
_TIME_LOCAL_APPARENT = 3
_CAL_GREGORIAN = 0
_CAL_JULIAN = 1

# The classic Morinus natal/radix .hor header contains 24 integer values before
# any optional trailing payload. The order is the same one used by Morinus'
# chart.Time and chart.Place constructors:
#
#   male, chart_type, bc,
#   year, month, day, hour, minute, second,
#   calendar, time_type, zone_plus, zone_hour, zone_minute, daylight_saving,
#   lon_deg, lon_min, lon_sec, east,
#   lat_deg, lat_min, lat_sec, north, altitude
_MIN_HEADER_INTS = 24

_UNICODE_ESCAPE_RE = re.compile(r"\\u([0-9a-fA-F]{4})")


def _decode_morinus_text(value: str) -> str:
    """Decode the ``\\uXXXX`` escapes used in Morinus protocol-0 strings."""
    return _UNICODE_ESCAPE_RE.sub(lambda m: chr(int(m.group(1), 16)), value)


def _extract_strings(raw_text: str) -> tuple[str | None, str | None]:
    """Return ``(chart_name, place_name)`` from protocol-0 V/.V strings."""
    name: str | None = None
    place: str | None = None
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if name is None and line.startswith("V") and not line.startswith(".V"):
            candidate = line[1:].strip()
            if candidate:
                name = _decode_morinus_text(candidate)
        elif place is None and line.startswith(".V"):
            candidate = line[2:].strip()
            if candidate:
                place = _decode_morinus_text(candidate)
    return name, place


def _extract_header_ints(raw_text: str) -> list[int]:
    values = [int(m.group(1)) for m in re.finditer(r"\.I(-?\d+)", raw_text)]
    if len(values) < _MIN_HEADER_INTS:
        raise HorParseError(
            f"Morinus header is incomplete: expected at least {_MIN_HEADER_INTS} integer "
            f"fields, found {len(values)}."
        )
    return values


def _validate_flag(name: str, value: int) -> bool:
    if value not in (0, 1):
        raise HorParseError(f"Invalid Morinus {name} flag: {value!r}; expected 0 or 1.")
    return bool(value)


def _validate_range(name: str, value: int, minimum: int, maximum: int) -> int:
    if not minimum <= value <= maximum:
        raise HorParseError(
            f"Invalid Morinus {name}: {value!r}; expected {minimum}..{maximum}."
        )
    return value


def _parse_datetime_and_offset(values: list[int], longitude: float) -> tuple[datetime, float]:
    """Parse Morinus civil time and return ``(UTC datetime, civil UTC offset)``."""
    bc = _validate_flag("BC", values[2])
    if bc:
        raise HorParseError("BC charts are not supported by hor-tools yet.")

    year, month, day, hour, minute, second = values[3:9]
    _validate_range("year", year, 1, 9999)
    _validate_range("month", month, 1, 12)
    _validate_range("hour", hour, 0, 23)
    _validate_range("minute", minute, 0, 59)
    _validate_range("second", second, 0, 59)
    try:
        dt_local = datetime(year, month, day, hour, minute, second)
    except ValueError as exc:
        raise HorParseError(f"Invalid Morinus calendar date/time: {exc}") from exc

    calendar = values[9]
    if calendar == _CAL_JULIAN:
        raise HorParseError("Julian-calendar .hor files are not supported yet.")
    if calendar != _CAL_GREGORIAN:
        raise HorParseError(f"Unknown Morinus calendar code: {calendar!r}.")

    time_type = values[10]
    if time_type not in {
        _TIME_ZONE,
        _TIME_GREENWICH,
        _TIME_LOCAL_MEAN,
        _TIME_LOCAL_APPARENT,
    }:
        raise HorParseError(f"Unknown Morinus time-type code: {time_type!r}.")

    plus = _validate_flag("zone direction", values[11])
    zone_hour = _validate_range("zone hour", values[12], 0, 12)
    zone_minute = _validate_range("zone minute", values[13], 0, 59)
    daylight = _validate_flag("daylight-saving", values[14])

    if time_type == _TIME_ZONE:
        base_offset = zone_hour + zone_minute / 60.0
        if not plus:
            base_offset *= -1.0
    elif time_type == _TIME_GREENWICH:
        base_offset = 0.0
    elif time_type == _TIME_LOCAL_MEAN:
        base_offset = longitude / 15.0
    else:
        raise HorParseError("Local-apparent-time .hor files are not supported yet.")

    tz_offset_hours = base_offset + (1.0 if daylight else 0.0)
    dt_utc = (dt_local - timedelta(hours=tz_offset_hours)).replace(tzinfo=timezone.utc)
    return dt_utc, tz_offset_hours


def _parse_place(values: list[int]) -> tuple[float, float, float]:
    """Return ``(latitude, longitude, altitude_m)`` from the Morinus header."""
    (
        lon_deg,
        lon_min,
        lon_sec,
        east_raw,
        lat_deg,
        lat_min,
        lat_sec,
        north_raw,
        altitude,
    ) = values[15:24]

    _validate_range("longitude degrees", lon_deg, 0, 180)
    _validate_range("longitude minutes", lon_min, 0, 59)
    _validate_range("longitude seconds", lon_sec, 0, 59)
    _validate_range("latitude degrees", lat_deg, 0, 90)
    _validate_range("latitude minutes", lat_min, 0, 59)
    _validate_range("latitude seconds", lat_sec, 0, 59)
    _validate_range("altitude", altitude, 0, 10000)
    east = _validate_flag("east/west", east_raw)
    north = _validate_flag("north/south", north_raw)

    longitude = lon_deg + lon_min / 60.0 + lon_sec / 3600.0
    latitude = lat_deg + lat_min / 60.0 + lat_sec / 3600.0
    if not east:
        longitude *= -1.0
    if not north:
        latitude *= -1.0

    if not -180.0 <= longitude <= 180.0:
        raise HorParseError(f"Longitude out of range after decoding: {longitude}.")
    if not -90.0 <= latitude <= 90.0:
        raise HorParseError(f"Latitude out of range after decoding: {latitude}.")

    return latitude, longitude, float(altitude)


def load_hor(path: str | Path) -> ChartInput:
    """Parse a supported Morinus ``.hor`` file into a validated ``ChartInput``."""
    file_path = Path(path).expanduser()
    if not file_path.is_file():
        raise FileNotFoundError(f".hor file not found: {file_path}")

    try:
        raw_text = file_path.read_text(encoding="ascii", errors="strict")
    except UnicodeDecodeError as exc:
        raise HorParseError("The .hor file is not valid Morinus ASCII protocol-0 data.") from exc

    values = _extract_header_ints(raw_text)
    male = _validate_flag("male", values[0])
    name, location_name = _extract_strings(raw_text)
    latitude, longitude, altitude_m = _parse_place(values)
    dt_utc, tz_offset_hours = _parse_datetime_and_offset(values, longitude)

    return ChartInput(
        name=name or file_path.stem,
        datetime_utc=dt_utc,
        tz_offset_hours=tz_offset_hours,
        latitude=latitude,
        longitude=longitude,
        house_system="W",
        zodiac="T",
        location_name=location_name,
        altitude_m=altitude_m,
        male=male,
    )
