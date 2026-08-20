#!/usr/bin/env python3
"""Scan a date window for Ascendant sign changes using a template .hor file."""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Iterable, List, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from hor_tools import astro_engine, hor_parser, output
from hor_tools.analysis import build_reports
from hor_tools.models import ChartInput

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

DEFAULT_OUTPUT_DIR = Path("outputs")


def parse_date(value: str) -> date:
    value = value.strip()
    try:
        y, m, d = value.split("-")
        return date(int(y), int(m), int(d))
    except Exception:
        return datetime.fromisoformat(value).date()


def parse_time(value: str) -> time:
    value = value.strip()
    try:
        h_str, m_str = value.split(":")
        h, m = int(h_str), int(m_str)
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
        return time(hour=h, minute=m)
    except Exception:
        return datetime.fromisoformat(value).time()


def daterange(start: date, end: date) -> Iterable[date]:
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)


def _fixed_template_zone(template: ChartInput) -> tzinfo:
    return timezone(timedelta(hours=template.tz_offset_hours))


def resolve_zone(template: ChartInput, zone_name: str | None) -> tzinfo:
    """Use an IANA zone when supplied; otherwise preserve the .hor fixed offset."""
    if not zone_name:
        return _fixed_template_zone(template)
    try:
        return ZoneInfo(zone_name)
    except ZoneInfoNotFoundError as exc:
        raise SystemExit(f"Unknown IANA timezone: {zone_name}") from exc


def offset_hours_at(dt_utc: datetime, zone: tzinfo) -> float:
    offset = dt_utc.astimezone(zone).utcoffset()
    return (offset.total_seconds() / 3600.0) if offset is not None else 0.0


def chart_at(template: ChartInput, dt_utc: datetime, zone: tzinfo | None = None) -> ChartInput:
    """Return template metadata at a new instant, updating civil offset if needed."""
    if zone is None:
        return replace(template, datetime_utc=dt_utc)
    return replace(
        template,
        datetime_utc=dt_utc,
        tz_offset_hours=offset_hours_at(dt_utc, zone),
    )


def asc_sign_at(template: ChartInput, dt_utc: datetime, zone: tzinfo | None = None) -> Tuple[int, float]:
    chart = chart_at(template, dt_utc, zone)
    houses = astro_engine.compute_houses(chart)
    asc = houses.asc
    return int(asc // 30), asc


def refine_asc_change(
    template: ChartInput,
    t0: datetime,
    t1: datetime,
    sign0: int,
    tol_minutes: float,
    zone: tzinfo | None = None,
) -> Tuple[datetime, int, float]:
    for _ in range(64):
        if (t1 - t0).total_seconds() <= tol_minutes * 60:
            break
        mid = t0 + (t1 - t0) / 2
        sign_mid, _ = asc_sign_at(template, mid, zone)
        if sign_mid == sign0:
            t0 = mid
        else:
            t1 = mid
    final_sign, asc_lon = asc_sign_at(template, t1, zone)
    return t1, final_sign, asc_lon


def to_utc_local(template: ChartInput, d: date, t: time, zone: tzinfo | None = None) -> datetime:
    """Interpret a requested clock time in the real local timezone, then convert to UTC."""
    local_zone = zone or _fixed_template_zone(template)
    dt_local = datetime.combine(d, t, tzinfo=local_zone)
    return dt_local.astimezone(timezone.utc)


def scan_asc_changes(
    template: ChartInput,
    start_date: date,
    end_date: date,
    window_start: time,
    window_end: time,
    step_minutes: float,
    tol_minutes: float,
    zone: tzinfo | None = None,
) -> List[Tuple[datetime, int, float]]:
    events: List[Tuple[datetime, int, float]] = []
    step = timedelta(minutes=step_minutes)

    for d in daterange(start_date, end_date):
        t_start_utc = to_utc_local(template, d, window_start, zone)
        t_end_utc = to_utc_local(template, d, window_end, zone)
        if t_end_utc <= t_start_utc:
            continue

        t0 = t_start_utc
        sign0, _ = asc_sign_at(template, t0, zone)
        while t0 < t_end_utc:
            t1 = min(t0 + step, t_end_utc)
            sign1, _ = asc_sign_at(template, t1, zone)
            if sign1 != sign0:
                when, final_sign, asc_lon = refine_asc_change(
                    template, t0, t1, sign0, tol_minutes, zone
                )
                events.append((when, final_sign, asc_lon))
                sign0 = final_sign
            else:
                sign0 = sign1
            t0 = t1

    events.sort(key=lambda x: x[0])
    return events


def resolve_output_path(path_str: str | None, start: date, end: date) -> Path:
    if path_str:
        p = Path(path_str)
        if not p.is_absolute() and p.parent == Path("."):
            p = DEFAULT_OUTPUT_DIR / p
    else:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        p = DEFAULT_OUTPUT_DIR / f"asc_scan_{start.isoformat()}_{end.isoformat()}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate reports for every Ascendant sign change within a date/time window."
    )
    parser.add_argument("--primer", required=True, help="Template .hor file to reuse location/house/zodiac.")
    parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD).")
    parser.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD, inclusive).")
    parser.add_argument("--window-start", default="00:00", help="Daily window start local time (HH:MM).")
    parser.add_argument("--window-end", default="23:59", help="Daily window end local time (HH:MM).")
    parser.add_argument("--step-min", type=float, default=15.0, help="Coarse step in minutes.")
    parser.add_argument("--tol-min", type=float, default=0.2, help="Refinement tolerance in minutes.")
    parser.add_argument("--out", help="Output Markdown path.")
    parser.add_argument("--ephe", help="Optional Swiss Ephemeris directory.")
    parser.add_argument("--verbose", action="store_true", help="Include full report (with Almuten tables).")
    parser.add_argument(
        "--tz",
        help="IANA timezone for DST-safe local windows, e.g. Europe/Belgrade. "
             "If omitted, the fixed offset stored in the .hor file is used.",
    )
    args = parser.parse_args()

    start_d = parse_date(args.start_date)
    end_d = parse_date(args.end_date)
    if end_d < start_d:
        raise SystemExit("End date must be on or after start date.")

    window_start = parse_time(args.window_start)
    window_end = parse_time(args.window_end)
    primer_path = Path(args.primer)
    if not primer_path.exists():
        raise SystemExit(f"Primer file not found: {primer_path}")

    template_chart = hor_parser.load_hor(primer_path)
    zone = resolve_zone(template_chart, args.tz)
    if args.ephe:
        astro_engine.set_ephe_path(args.ephe)

    if not args.tz:
        print(
            "Warning: no --tz supplied; using the .hor file's fixed UTC offset. "
            "Use an IANA timezone for scans that may cross a DST transition."
        )

    events = scan_asc_changes(
        template_chart, start_d, end_d, window_start, window_end,
        args.step_min, args.tol_min, zone,
    )
    if not events:
        raise SystemExit("No Ascendant sign changes found in the given window.")

    output_path = resolve_output_path(args.out, start_d, end_d)
    zone_label = args.tz or f"fixed UTC{template_chart.tz_offset_hours:+}"
    header_lines = [
        "# Ascendant Change Reports", "",
        f"Primer: {primer_path}",
        f"Date window: {start_d} to {end_d}",
        f"Daily time window (local): {window_start}–{window_end}",
        f"Timezone: {zone_label}",
        f"Ephemeris: {args.ephe or 'default'}", "",
    ]

    sections: List[str] = ["\n".join(header_lines)]
    for dt_utc, asc_idx, asc_lon in events:
        dt_local = dt_utc.astimezone(zone)
        chart = chart_at(template_chart, dt_utc, zone)
        planets = astro_engine.compute_planets(chart)
        houses = astro_engine.compute_houses(chart)
        reports, relationships = build_reports(chart, planets, houses)
        md = output.build_markdown_report(
            chart, reports, houses, planets, relationships,
            include_almuten=args.verbose,
        )
        header = [
            f"## {SIGNS[asc_idx]} rising — {dt_local.isoformat()} (local) / {dt_utc.isoformat()}Z",
            f"- Asc @ {asc_lon:.2f}°", "",
        ]
        sections.append("\n".join(header) + "\n" + md)

    output_path.write_text("\n\n".join(sections), encoding="utf-8")
    print(f"Wrote {len(events)} reports to {output_path.resolve()}")


if __name__ == "__main__":
    main()
