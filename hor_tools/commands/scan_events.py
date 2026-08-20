"""Scan date ranges for planetary ingresses and exact aspects."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from typing import Iterable, Sequence

from ..astro_engine import compute_longitudes, set_ephe_path
from ..models import ChartInput

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

DEFAULT_ASPECTS = {
    0.0: "conjunction",
    60.0: "sextile",
    90.0: "square",
    120.0: "trine",
    180.0: "opposition",
}


def parse_dt(value: str) -> datetime:
    """Return a UTC datetime from an ISO-like string."""
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid ISO datetime: {value!r}") from exc

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
    value = normalize_angle(angle)
    if value > 180:
        value -= 360
    return value


def directed_angle(lon1: float, lon2: float) -> float:
    """Directed zodiacal angle from ``lon1`` to ``lon2`` in [0, 360)."""
    return (lon2 - lon1) % 360.0


def angle_between(lon1: float, lon2: float) -> float:
    """Smallest signed angle from ``lon1`` to ``lon2``."""
    return shortest_angle(lon2 - lon1)


def aspect_separation(lon1: float, lon2: float) -> float:
    return abs(angle_between(lon1, lon2))


def _unwrap_near(value: float, reference: float) -> float:
    """Shift a 0-360 angle by whole turns so it lies nearest ``reference``."""
    value = float(value)
    while value - reference > 180.0:
        value -= 360.0
    while value - reference <= -180.0:
        value += 360.0
    return value


def _crossed_aspect_target(rel0: float, rel1: float, aspect_deg: float) -> float | None:
    """Return the unwrapped exact aspect branch crossed between two samples."""
    rel1_unwrapped = _unwrap_near(rel1, rel0)
    lo, hi = sorted((rel0, rel1_unwrapped))
    branches = {float(aspect_deg) % 360.0, (-float(aspect_deg)) % 360.0}
    for branch in branches:
        for turn in (-1, 0, 1, 2):
            target = branch + 360.0 * turn
            if lo <= target <= hi:
                return target
    return None


def positions_at(dt_utc: datetime, lat: float, lon: float) -> dict[str, float]:
    """Return only the longitudes needed by the scanner."""
    return compute_longitudes(chart_for(dt_utc, lat, lon))


def _validate_scan_parameters(
    start: datetime,
    end: datetime,
    lat: float,
    lon: float,
    step_minutes: float,
    tol_minutes: float,
) -> None:
    if end <= start:
        raise ValueError("end datetime must be after start datetime")
    if step_minutes <= 0:
        raise ValueError("step-min must be greater than zero")
    if tol_minutes <= 0:
        raise ValueError("tol-min must be greater than zero")
    if not -90.0 <= lat <= 90.0:
        raise ValueError("latitude must be between -90 and 90 degrees")
    if not -180.0 <= lon <= 180.0:
        raise ValueError("longitude must be between -180 and 180 degrees")


def refine_ingress(
    planet: str,
    t0: datetime,
    t1: datetime,
    lat: float,
    lon: float,
    tol_minutes: float,
) -> tuple[datetime, float]:
    if tol_minutes <= 0:
        raise ValueError("tol-min must be greater than zero")

    pos_t0 = positions_at(t0, lat, lon)[planet]
    sign0 = sign_index(pos_t0)
    for _ in range(48):
        if (t1 - t0).total_seconds() <= tol_minutes * 60:
            break
        mid = t0 + (t1 - t0) / 2
        pos_mid = positions_at(mid, lat, lon)[planet]
        if sign_index(pos_mid) == sign0:
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
) -> tuple[datetime, float]:
    """Binary-search an already bracketed exact aspect branch."""
    if tol_minutes <= 0:
        raise ValueError("tol-min must be greater than zero")

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
        d_mid = delta(mid)
        if abs(d_mid) < 1e-12:
            t0 = t1 = mid
            break
        if (d0 <= 0 <= d_mid) or (d0 >= 0 >= d_mid):
            t1 = mid
        else:
            t0 = mid
            d0 = d_mid

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
    aspects: dict[float, str],
) -> tuple[
    list[tuple[datetime, str, str, float]],
    list[tuple[datetime, str, str, str, float]],
]:
    _validate_scan_parameters(start, end, lat, lon, step_minutes, tol_minutes)

    ingress_events: list[tuple[datetime, str, str, float]] = []
    aspect_events: list[tuple[datetime, str, str, str, float]] = []
    planets = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]

    t_prev = start
    pos_prev = positions_at(t_prev, lat, lon)
    step = timedelta(minutes=step_minutes)

    while t_prev < end:
        t_next = min(t_prev + step, end)
        pos_next = positions_at(t_next, lat, lon)

        for planet in planets:
            if sign_index(pos_prev[planet]) != sign_index(pos_next[planet]):
                when, lon_exact = refine_ingress(
                    planet, t_prev, t_next, lat, lon, tol_minutes
                )
                ingress_events.append(
                    (when, planet, SIGNS[sign_index(lon_exact)], lon_exact)
                )

        for index, p1 in enumerate(planets):
            for p2 in planets[index + 1 :]:
                rel_prev = directed_angle(pos_prev[p1], pos_prev[p2])
                rel_next = directed_angle(pos_next[p1], pos_next[p2])
                for degree, label in aspects.items():
                    target = _crossed_aspect_target(rel_prev, rel_next, degree)
                    if target is None:
                        continue
                    when, angle_exact = refine_aspect(
                        p1, p2, target, t_prev, t_next, lat, lon, tol_minutes
                    )
                    event = (when, p1, p2, label, angle_exact)
                    duplicate_endpoint = (
                        aspect_events
                        and event[:4] == aspect_events[-1][:4]
                        and abs((when - aspect_events[-1][0]).total_seconds())
                        <= tol_minutes * 60
                    )
                    if not duplicate_endpoint:
                        aspect_events.append(event)

        t_prev, pos_prev = t_next, pos_next

    ingress_events.sort(key=lambda item: item[0])
    aspect_events.sort(key=lambda item: item[0])
    return ingress_events, aspect_events


def parse_aspects(values: Iterable[str]) -> dict[float, str]:
    aspects: dict[float, str] = {}
    for value in values:
        if "=" in value:
            degree_text, name = value.split("=", 1)
        else:
            degree_text, name = value, f"{value}°"
        try:
            degree = float(degree_text)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"invalid aspect degree: {degree_text!r}") from exc
        if not 0.0 <= degree <= 180.0:
            raise argparse.ArgumentTypeError("aspect degrees must be between 0 and 180")
        aspects[degree] = name
    return aspects


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hor-scan-events",
        description="List sign ingresses and exact aspects in a UTC date range.",
    )
    parser.add_argument("--start", required=True, type=parse_dt, help="Start ISO datetime.")
    parser.add_argument("--end", required=True, type=parse_dt, help="End ISO datetime.")
    parser.add_argument("--lat", required=True, type=float, help="Latitude in decimal degrees.")
    parser.add_argument("--lon", required=True, type=float, help="Longitude in decimal degrees.")
    parser.add_argument("--step-min", type=float, default=60.0, help="Coarse step in minutes.")
    parser.add_argument("--tol-min", type=float, default=0.1, help="Refinement tolerance in minutes.")
    parser.add_argument(
        "--aspect",
        action="append",
        default=[],
        help="Aspect in DEG=name form; repeatable.",
    )
    parser.add_argument("--ephe", help="Swiss Ephemeris directory.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.ephe:
        set_ephe_path(args.ephe)

    try:
        aspects = parse_aspects(args.aspect) if args.aspect else DEFAULT_ASPECTS
        ingress_events, aspect_events = scan_range(
            args.start,
            args.end,
            args.lat,
            args.lon,
            args.step_min,
            args.tol_min,
            aspects,
        )
    except (ValueError, RuntimeError) as exc:
        parser.exit(2, f"{parser.prog}: error: {exc}\n")

    print("\nIngresses")
    print("---------")
    for when, planet, sign, longitude in ingress_events:
        print(f"{when.isoformat()} UTC: {planet} enters {sign} at {longitude:.2f}°")

    print("\nAspects")
    print("-------")
    for when, p1, p2, label, angle in aspect_events:
        print(f"{when.isoformat()} UTC: {p1} {label} {p2} (angle {angle:.2f}°)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
