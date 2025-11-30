#!/usr/bin/env python3
"""Scan a date range for sign ingresses and exact aspects using hor_tools + Swiss Ephemeris.

This is intentionally standalone: it imports the project as a library and does not
modify existing code. You can place it anywhere (inside or outside the repo) as long
as hor_tools is importable and ephemeris files are available.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Tuple

from hor_tools.astro_engine import compute_planets, set_ephe_path
from hor_tools.models import ChartInput


SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]

# Traditional aspects; override via CLI if needed.
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

    # First, try the built-in ISO parser.
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        # Try a few common patterns that accept 1-digit month/day.
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
    """Build a ChartInput for the given UTC datetime and location."""

    return ChartInput(
        name="transit",
        datetime_utc=dt_utc,
        tz_offset_hours=0.0,
        latitude=lat,
        longitude=lon,
        house_system="WholeSign",
        zodiac="Tropical",
    )


def sign_index(longitude: float) -> int:
    return int(longitude // 30)


def normalize_angle(angle: float) -> float:
    """Normalize to [0, 360)."""

    return angle % 360.0


def shortest_angle(angle: float) -> float:
    """Normalize to (-180, 180]."""

    a = normalize_angle(angle)
    if a > 180:
        a -= 360
    return a


def angle_between(lon1: float, lon2: float) -> float:
    """Smallest signed angle from lon1 to lon2."""

    return shortest_angle(lon2 - lon1)


def positions_at(dt_utc: datetime, lat: float, lon: float) -> Dict[str, float]:
    """Return ecliptic longitudes for planets at a given time/location."""

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
    """Binary search for the ingress time within [t0, t1]."""

    pos_t0 = positions_at(t0, lat, lon)[planet]
    s0 = sign_index(pos_t0)
    for _ in range(48):
        if (t1 - t0).total_seconds() <= tol_minutes * 60:
            break
        mid = t0 + (t1 - t0) / 2
        pos_mid = positions_at(mid, lat, lon)[planet]
        s_mid = sign_index(pos_mid)
        if s_mid == s0:
            t0 = mid
            pos_t0 = pos_mid
            s0 = s_mid
        else:
            t1 = mid
    final_pos = positions_at(t1, lat, lon)[planet]
    return t1, final_pos


def refine_aspect(
    p1: str,
    p2: str,
    aspect_deg: float,
    t0: datetime,
    t1: datetime,
    lat: float,
    lon: float,
    tol_minutes: float,
) -> Tuple[datetime, float]:
    """Binary search for exact aspect perfection within [t0, t1]."""

    def delta(dt: datetime) -> float:
        pos = positions_at(dt, lat, lon)
        diff = angle_between(pos[p1], pos[p2])
        return diff - aspect_deg

    d0 = delta(t0)
    for _ in range(48):
        if (t1 - t0).total_seconds() <= tol_minutes * 60:
            break
        mid = t0 + (t1 - t0) / 2
        d_mid = delta(mid)
        if d_mid == 0:
            t0 = t1 = mid
            break
        if d0 == 0:
            t0 = mid
            d0 = d_mid
            continue
        if (d0 > 0 and d_mid > 0) or (d0 < 0 and d_mid < 0):
            t0 = mid
            d0 = d_mid
        else:
            t1 = mid
    final_dt = t1
    final_pos = positions_at(final_dt, lat, lon)
    angle_now = angle_between(final_pos[p1], final_pos[p2])
    return final_dt, angle_now


def scan_range(
    start: datetime,
    end: datetime,
    lat: float,
    lon: float,
    step_minutes: float,
    tol_minutes: float,
    aspects: Dict[float, str],
) -> Tuple[List[Tuple[datetime, str, str, float]], List[Tuple[datetime, str, str, str, float]]]:
    """Return ingress events and aspect events found in the interval."""

    ingress_events: List[Tuple[datetime, str, str, float]] = []
    aspect_events: List[Tuple[datetime, str, str, str, float]] = []

    planets = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
    t_prev = start
    pos_prev = positions_at(t_prev, lat, lon)

    while t_prev < end:
        t_next = min(t_prev + timedelta(minutes=step_minutes), end)
        pos_next = positions_at(t_next, lat, lon)

        # Ingress detection
        for pl in planets:
            if sign_index(pos_prev[pl]) != sign_index(pos_next[pl]):
                when, lon_exact = refine_ingress(pl, t_prev, t_next, lat, lon, tol_minutes)
                ingress_events.append((when, pl, SIGNS[sign_index(lon_exact)], lon_exact))

        # Aspect detection
        for i, p1 in enumerate(planets):
            for p2 in planets[i + 1 :]:
                angle_prev = angle_between(pos_prev[p1], pos_prev[p2])
                angle_next = angle_between(pos_next[p1], pos_next[p2])
                for deg, label in aspects.items():
                    delta_prev = angle_prev - deg
                    delta_next = angle_next - deg
                    if delta_prev == 0:
                        aspect_events.append((t_prev, p1, p2, label, angle_prev))
                        continue
                    if delta_prev > 0 > delta_next or delta_prev < 0 < delta_next:
                        when, angle_exact = refine_aspect(p1, p2, deg, t_prev, t_next, lat, lon, tol_minutes)
                        aspect_events.append((when, p1, p2, label, angle_exact))

        t_prev, pos_prev = t_next, pos_next

    ingress_events.sort(key=lambda x: x[0])
    aspect_events.sort(key=lambda x: x[0])
    return ingress_events, aspect_events


def parse_aspects(values: Iterable[str]) -> Dict[float, str]:
    """Parse custom aspects like 0=conj,60=sextile."""

    aspects: Dict[float, str] = {}
    for val in values:
        if "=" in val:
            deg_str, name = val.split("=", 1)
        else:
            deg_str, name = val, f"{val}°"
        deg = float(deg_str)
        aspects[deg] = name
    return aspects


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List sign ingresses and exact aspects in a date range (UTC)."
    )
    parser.add_argument("--start", required=True, help="Start datetime (ISO, accepts timezone).")
    parser.add_argument("--end", required=True, help="End datetime (ISO, accepts timezone).")
    parser.add_argument("--lat", required=True, type=float, help="Latitude in decimal degrees.")
    parser.add_argument("--lon", required=True, type=float, help="Longitude in decimal degrees.")
    parser.add_argument(
        "--step-min",
        type=float,
        default=60.0,
        help="Step size in minutes for coarse scan (default: 60).",
    )
    parser.add_argument(
        "--tol-min",
        type=float,
        default=0.1,
        help="Refinement tolerance in minutes for event times (default: 0.1).",
    )
    parser.add_argument(
        "--aspect",
        action="append",
        default=[],
        help="Aspect in form DEG=name (e.g., 72=quintile). Repeatable. Defaults to traditional set.",
    )
    parser.add_argument(
        "--ephe",
        help="Optional Swiss Ephemeris directory. Defaults to SWISSEPH_EPHE env or project default.",
    )
    args = parser.parse_args()

    # Friendly reminder if the template placeholder wasn't replaced.
    if "<" in args.start or ">" in args.start:
        sys.exit("Replace the start datetime placeholder with an ISO timestamp (e.g. 2027-10-01T00:00:00Z).")
    if "<" in args.end or ">" in args.end:
        sys.exit("Replace the end datetime placeholder with an ISO timestamp (e.g. 2027-11-01T00:00:00Z).")

    if args.ephe:
        set_ephe_path(args.ephe)

    start_dt = parse_dt(args.start)
    end_dt = parse_dt(args.end)
    if end_dt <= start_dt:
        raise SystemExit("End datetime must be after start datetime.")

    aspects = parse_aspects(args.aspect) if args.aspect else DEFAULT_ASPECTS

    ingress_events, aspect_events = scan_range(
        start=start_dt,
        end=end_dt,
        lat=args.lat,
        lon=args.lon,
        step_minutes=args.step_min,
        tol_minutes=args.tol_min,
        aspects=aspects,
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
