"""Parsing utilities for Morinus .hor files."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import ChartInput


def load_hor(path: str | Path) -> ChartInput:
    """Parse a Morinus .hor file into a normalized ChartInput."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f".hor file not found: {file_path}")

    raw_text = file_path.read_text(encoding="ascii", errors="replace")
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    # Name: first line starting with 'V' but not '.V'
    name_line = next((ln for ln in lines if ln.startswith("V") and not ln.startswith(".V")), None)
    if name_line:
        name = name_line[1:].strip()
    else:
        # Fallback for "Here and now" or other Morinus exports that omit a V-name line.
        # Try to grab the first quoted string (S'...') from the pickle text, else use the filename stem.
        quoted_match = re.search(r"S'([^']*)'", raw_text)
        if quoted_match:
            name = quoted_match.group(1) or file_path.stem
        else:
            name = file_path.stem

    # Collect all integer fields in order
    ints: list[int] = [int(m.group(1)) for m in re.finditer(r"\.I(-?\d+)", raw_text)]
    if not ints:
        # Fallback: try any bare integers in the file if .I tags are missing.
        ints = [int(m.group(1)) for m in re.finditer(r"\b(-?\d+)\b", raw_text)]
    if not ints:
        raise ValueError("No numeric entries found in .hor file.")

    # 1) Get date/time and coordinates (they do not depend on timezone)
    year, month, day, hour, minute, second = _extract_datetime(ints)
    latitude, longitude = _parse_coordinates(ints)

    # 2) Read timezone + DST exactly as stored in the .hor file
    zone_hours, zone_minutes, dst_flag = _extract_timezone_fields(ints)
    tz_offset_hours = _tz_offset_hours(zone_hours, zone_minutes, dst_flag)

    # Morinus stores local civil time. Convert explicitly to true UTC.
    dt_local = datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second)
    dt_utc = (dt_local - timedelta(hours=tz_offset_hours)).replace(tzinfo=timezone.utc)

    return ChartInput(
        name=name,
        datetime_utc=dt_utc,
        tz_offset_hours=tz_offset_hours,
        latitude=latitude,
        longitude=longitude,
        house_system="W",  # Whole sign
        zodiac="T",  # Tropical
    )


def _extract_timezone_fields(values: list[int]) -> tuple[int, int, int]:
    """
    Extract timezone and DST flag from the .hor header.

    Morinus natal files store the timezone block near the middle of the int
    stream, immediately before the coordinate block:
        [..., tz_sign, tz_hours, tz_minutes, dst_flag, lon_deg, ...]

    - tz_sign is 1 for east of Greenwich, 0/-1 for west (we default 0 -> east)
    - tz_hours / tz_minutes are absolute values
    - dst_flag is 1 if the user checked the “DST” box in Morinus

    Fall back to the legacy assumption (first 3 ints) if the block is missing.
    """
    if len(values) >= 15:
        tz_sign_raw = values[11]
        tz_sign = 1 if tz_sign_raw >= 0 else -1
        zone_hours = tz_sign * abs(values[12])
        zone_minutes = tz_sign * abs(values[13])
        dst_flag = values[14]
        # If everything is zero, fall back to the legacy block below.
        if zone_hours or zone_minutes or dst_flag:
            return zone_hours, zone_minutes, dst_flag

    # Legacy fallback: first three ints (older heuristic)
    zone_hours = values[0] if len(values) >= 1 else 0
    zone_minutes = values[1] if len(values) >= 2 else 0
    dst_flag = values[2] if len(values) >= 3 else 0
    return zone_hours, zone_minutes, dst_flag


def _tz_offset_hours(zone_hours: int, zone_minutes: int, dst_flag: int) -> float:
    """
    Combine base zone and DST flag into a single offset in hours.

    Morinus lets the user tick DST manually, so:
      base_offset = zone_hours + zone_minutes / 60
      offset = base_offset + (1 if dst_flag else 0)
    """
    base_offset = zone_hours + zone_minutes / 60.0
    return float(base_offset + (1 if dst_flag else 0))


def _extract_datetime(values: list[int]) -> tuple[int, int, int, int, int, int]:
    """
    Find the date/time block.

    We search for the first 4-digit year and assume:
        [year, month, day, hour, minute, second?]
    """
    for idx, value in enumerate(values):
        if value >= 1000:  # very likely the year
            if len(values) < idx + 5:
                break
            year = value
            month = values[idx + 1]
            day = values[idx + 2]
            hour = values[idx + 3]
            minute = values[idx + 4]
            second = values[idx + 5] if len(values) > idx + 5 else 0
            return year, month, day, hour, minute, second

    # Fallback: assume the first 6 numbers are Y/M/D/H/M/S
    if len(values) >= 5:
        year, month, day, hour, minute = values[:5]
        second = values[5] if len(values) >= 6 else 0
        return year, month, day, hour, minute, second

    raise ValueError("Year not found in .hor integer stream.")


def _parse_coordinates(values: list[int]) -> tuple[float, float]:
    """
    Coordinates heuristic.

    In Morinus natal .hor files the last 9 ints are typically:
        [lon_deg, lon_min, lon_sec, east_flag,
         lat_deg, lat_min, lat_sec, north_flag,
         altitude]

    We ignore altitude and use the first 8.

    Returns:
        (latitude, longitude) in decimal degrees.
    """
    if len(values) < 8:
        return 0.0, 0.0

    coord_block = values[-9:-1] if len(values) >= 9 else values[-8:]
    if len(coord_block) < 8:
        coord_block = values[-8:] if len(values) >= 8 else values
    if len(coord_block) < 8:
        return 0.0, 0.0

    # NOTE: longitude comes first in Morinus .hor, then latitude
    lon_deg, lon_min, lon_sec, east_flag, lat_deg, lat_min, lat_sec, north_flag = coord_block[:8]

    lat_sign = 1 if north_flag >= 1 else -1
    lon_sign = 1 if east_flag >= 1 else -1

    latitude = lat_sign * (abs(lat_deg) + lat_min / 60.0 + lat_sec / 3600.0)
    longitude = lon_sign * (abs(lon_deg) + lon_min / 60.0 + lon_sec / 3600.0)
    return latitude, longitude
