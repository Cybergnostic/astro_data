#!/usr/bin/env python3
"""Scan a date range for sign ingresses and exact aspects using hor_tools + Swiss Ephemeris."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Tuple

from hor_tools.astro_engine import compute_planets, set_ephe_path
from hor_tools.models import ChartInput

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

DEFAULT_ASPECTS = {
    0: "conjunction",
    60: "sextile",
    90: "square",
    120: "trine",
    180: "opposition",
}


def parse_dt(value: str) -> datetime:
    """Return a UTC datetime from an ISO-like string, lenient on 1-digit month/day."""
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"

    def try_parse(fmt: str) -> datetime | None:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            return None

    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        dt = (
            try_parse("%Y-%m-%dT%H:%M:%S%z")
            or try_parse("%Y-%m-%dT%H:%M:%S.%f%z")
            or try_parse("%Y-%m-%d %H:%M:%S%z")
            or try_parse("%Y-%m-%d %H:%M:%S.%f%z")
            or try_parse("%Y-%m-%dT%H:%M:%S")
            or try_parse("%Y-%m-%dT%H:%M:%S.%f")
        )
        if dt is None:
            raise

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def chart_for(dt_utc: datetime, lat: float, lon: float) -> ChartInput:
    return ChartInput(
        name="transit",
        datetime_utc=dt_utc,
        tz_offset_hours=0.0,
        latitude=lat,
        longitude=lon,
        house_system="W",
        zodiac="T",
    )


def sign_index(longitude: float) -> int:
    return int(longitude // 30) % 12


def normalize_angle(angle: float) -> float:
    return angle % 360.0


def shortest_angle(angle: float) -> float:
    a = normalize_angle(angle)
    if a > 180:
        a -= 360
    return a


def directed_angle(lon1: float, lon2: float) -> float:
    """Directed zodiacal angle from lon1 to lon2 in [0, 360)."""
    return (lon2 - lon1) % 360.0


def angle_between(lon1: float, lon2: float) -> float:
    """Smallest signed angle from lon1 to lon2, retained for compatibility."""
    return shortest_angle(lon2 - lon1)


def aspect_separation(lon1: float, lon2: float) -> float:
    return abs(angle_between(lon1, lon2))


def _unwrap_near(value: float, reference: float) -> float:
    """Shift a 0-360 angle by whole turns so it lies nearest reference."""
    value = float(value)
    while value - reference > 180.0:
        value -= 360.0
    while value - reference <= -180.0:
        value += 360.0
    return value


def _crossed_aspect_target(rel0: float, rel1: float, aspect_deg: float) -> float | None:
    """Return the unwrapped exact branch crossed between two directed angles."""
    rel1_u = _unwrap_near(rel1, rel0)
    lo, hi = sorted((rel0, rel1_u))
    branches = {float(aspect_deg) % 360.0, (-float(aspect_deg)) % 360.0}
    for branch in branches:
        for turn in (-1, 0, 1, 2):
            target = branch + 360.0 * turn
            if lo <= target <= hi:
                return target
    return None


def positions_at(dt_utc: datetime, lat: float, lon: float) -> Dict[str, float]:
    chart = chart_for(dt_utc, lat, lon)
    return {p.name: p.longitude for p in compute_planets(chart)}


def refine_ingress(
    planet: str,
    t0: datetime,
    t1: datetime,
    lat: float,
    lon: float,
    tol_minutes: float,
) -> Tuple[datetime, float]:
    pos_t0 = positions_at(t0, lat, lon)[planet]
    s0 = sign_index(pos_t0)
    for _ in range(48):
        if (t1 - t0).total_seconds() <= tol_minutes * 60:
            break
        mid = t0 + (t1 - t0) / 2
        pos_mid = positions_at(mid, lat, lon)[planet]
        if sign_index(pos_mid) == s0:
            t0 = mid
        else:
            t1 = mid
    final_pos = positions_at(t1, lat, lon)[planet]
    return t1, final_pos


def refine_aspect(
    p1: str,
    p2: str,
    target_unwrapped: float,
    t0: datetime,
    t1: datetime,
    lat: float,
    lon: float,
    tol_minutes: float,
) -> Tuple[datetime, float]:
    """Binary-search an already bracketed exact aspect branch."""
    pos0 = positions_at(t0, lat, lon)
    anchor = directed_angle(pos0[p1], pos0[p2])

    def delta(dt: datetime) -> float:
        pos = positions_at(dt, lat, lon)
        rel = _unwrap_near(directed_angle(pos[p1], pos[p2]), anchor)
        return rel - target_unwrapped

    d0 = delta(t0)
    for _ in range(48):
        if (t1 - t0).total_seconds() <= tol_minutes * 60:
            break
        mid = t0 + (t1 - t0) / 2
        dm = delta(mid)
        if abs(dm) < 1e-12:
            t0 = t1 = mid
            break
        if (d0 <= 0 <= dm) or (d0 >= 0 >= dm):
            t1 = mid
        else:
            t0 = mid
            d0 = dm

    final_dt = t1
    final_pos = positions_at(final_dt, lat, lon)
    return final_dt, aspect_separation(final_pos[p1], final_pos[p2])


def scan_range(
    start: datetime,
    end: datetime,
    lat: float,
    lon: float,
    step_minutes: float,
    tol_minutes: float,
    aspects: Dict[float, str],
) -> Tuple[List[Tuple[datetime, str, str, float]], List[Tuple[datetime, str, str, str, float]]]:
    ingress_events: List[Tuple[datetime, str, str, float]] = []
    aspect_events: List[Tuple[datetime, str, str, str, float]] = []

    planets = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
    t_prev = start
    pos_prev = positions_at(t_prev, lat, lon)

    while t_prev < end:
        t_next = min(t_prev + timedelta(minutes=step_minutes), end)
        pos_next = positions_at(t_next, lat, lon)

        for pl in planets:
            if sign_index(pos_prev[pl]) != sign_index(pos_next[pl]):
                when, lon_exact = refine_ingress(pl, t_prev, t_next, lat, lon, tol_minutes)
                ingress_events.append((when, pl, SIGNS[sign_index(lon_exact)], lon_exact))

        for i, p1 in enumerate(planets):
            for p2 in planets[i + 1:]:
                rel_prev = directed_angle(pos_prev[p1], pos_prev[p2])
                rel_next = directed_angle(pos_next[p1], pos_next[p2])
                for deg, label in aspects.items():
                    target = _crossed_aspect_target(rel_prev, rel_next, deg)
                    if target is None:
                        continue
                    when, angle_exact = refine_aspect(
                        p1, p2, target, t_prev, t_next, lat, lon, tol_minutes
                    )
                    event = (when, p1, p2, label, angle_exact)
                    # Adjacent scan windows can share an exact endpoint; avoid duplicates.
                    if not aspect_events or event[:4] != aspect_events[-1][:4] or abs((when - aspect_events[-1][0]).total_seconds()) > tol_minutes * 60:
                        aspect_events.append(event)

        t_prev, pos_prev = t_next, pos_next

    ingress_events.sort(key=lambda x: x[0])
    aspect_events.sort(key=lambda x: x[0])
    return ingress_events, aspect_events


def parse_aspects(values: Iterable[str]) -> Dict[float, str]:
    aspects: Dict[float, str] = {}
    for val in values:
        if "=" in val:
            deg_str, name = val.split("=", 1)
        else:
            deg_str, name = val, f"{val}°"
        aspects[float(deg_str)] = name
    return aspects


def main() -> None:
    parser = argparse.ArgumentParser(description="List sign ingresses and exact aspects in a date range (UTC).")
    parser.add_argument("--start", required=True, help="Start datetime (ISO, accepts timezone).")
    parser.add_argument("--end", required=True, help="End datetime (ISO, accepts timezone).")
    parser.add_argument("--lat", required=True, type=float, help="Latitude in decimal degrees.")
    parser.add_argument("--lon", required=True, type=float, help="Longitude in decimal degrees.")
    parser.add_argument("--step-min", type=float, default=60.0, help="Coarse step in minutes (default: 60).")
    parser.add_argument("--tol-min", type=float, default=0.1, help="Refinement tolerance in minutes (default: 0.1).")
    parser.add_argument("--aspect", action="append", default=[], help="Aspect in form DEG=name. Repeatable.")
    parser.add_argument("--ephe", help="Optional Swiss Ephemeris directory.")
    args = parser.parse_args()

    if "<" in args.start or ">" in args.start:
        sys.exit("Replace the start datetime placeholder with an ISO timestamp.")
    if "<" in args.end or ">" in args.end:
        sys.exit("Replace the end datetime placeholder with an ISO timestamp.")
    if args.ephe:
        set_ephe_path(args.ephe)

    start_dt = parse_dt(args.start)
    end_dt = parse_dt(args.end)
    if end_dt <= start_dt:
        raise SystemExit("End datetime must be after start datetime.")

    aspects = parse_aspects(args.aspect) if args.aspect else DEFAULT_ASPECTS
    ingress_events, aspect_events = scan_range(
        start_dt, end_dt, args.lat, args.lon, args.step_min, args.tol_min, aspects
    )

    print("\nIngresses")
    print("---------")
    for when, planet, sign, lon in ingress_events:
        print(f"{when.isoformat()} UTC: {planet} enters {sign} at {lon:.2f}°")

    print("\nAspects")
    print("-------")
    for when, p1, p2, label, angle in aspect_events:
        print(f"{when.isoformat()} UTC: {p1} {label} {p2} (angle {angle:.2f}°)")


if __name__ == "__main__":
    main()
