"""Scan date windows for Ascendant sign changes."""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Iterable, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .. import astro_engine, hor_parser, output
from ..analysis import build_reports
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

DEFAULT_OUTPUT_DIR = Path("outputs")


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid ISO date: {value!r}") from exc


def parse_time(value: str) -> time:
    raw = value.strip()
    try:
        parsed = time.fromisoformat(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid local time: {value!r}") from exc
    return parsed.replace(tzinfo=None)


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
        raise ValueError(f"unknown IANA timezone: {zone_name}") from exc


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


def asc_sign_at(
    template: ChartInput, dt_utc: datetime, zone: tzinfo | None = None
) -> tuple[int, float]:
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
) -> tuple[datetime, int, float]:
    if tol_minutes <= 0:
        raise ValueError("tol-min must be greater than zero")

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


def to_utc_local(
    template: ChartInput,
    day: date,
    local_time: time,
    zone: tzinfo | None = None,
) -> datetime:
    """Interpret a requested clock time in the local timezone and convert to UTC."""
    local_zone = zone or _fixed_template_zone(template)
    dt_local = datetime.combine(day, local_time, tzinfo=local_zone)
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
) -> list[tuple[datetime, int, float]]:
    if end_date < start_date:
        raise ValueError("end date must be on or after start date")
    if step_minutes <= 0:
        raise ValueError("step-min must be greater than zero")
    if tol_minutes <= 0:
        raise ValueError("tol-min must be greater than zero")
    if window_end <= window_start:
        raise ValueError(
            "window-end must be after window-start; overnight windows are not supported"
        )

    events: list[tuple[datetime, int, float]] = []
    step = timedelta(minutes=step_minutes)

    for day in daterange(start_date, end_date):
        t_start_utc = to_utc_local(template, day, window_start, zone)
        t_end_utc = to_utc_local(template, day, window_end, zone)

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

    events.sort(key=lambda item: item[0])
    return events


def resolve_output_path(path_str: str | None, start: date, end: date) -> Path:
    if path_str:
        path = Path(path_str).expanduser()
        if not path.is_absolute() and path.parent == Path("."):
            path = DEFAULT_OUTPUT_DIR / path
    else:
        path = DEFAULT_OUTPUT_DIR / f"asc_scan_{start.isoformat()}_{end.isoformat()}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hor-scan-asc",
        description="Generate reports for Ascendant sign changes in a local date/time window.",
    )
    parser.add_argument("--primer", required=True, type=Path, help="Template Morinus .hor file.")
    parser.add_argument("--start-date", required=True, type=parse_date, help="Start YYYY-MM-DD.")
    parser.add_argument("--end-date", required=True, type=parse_date, help="End YYYY-MM-DD.")
    parser.add_argument("--window-start", type=parse_time, default=time(0, 0))
    parser.add_argument("--window-end", type=parse_time, default=time(23, 59))
    parser.add_argument("--step-min", type=float, default=15.0, help="Coarse step in minutes.")
    parser.add_argument("--tol-min", type=float, default=0.2, help="Refinement tolerance in minutes.")
    parser.add_argument("--out", help="Output Markdown path.")
    parser.add_argument("--ephe", help="Swiss Ephemeris directory.")
    parser.add_argument("--verbose", action="store_true", help="Include full Almuten tables.")
    parser.add_argument(
        "--tz",
        help="IANA timezone for DST-safe local windows, e.g. Europe/Belgrade. "
        "If omitted, the fixed offset stored in the .hor file is used.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    primer_path = args.primer.expanduser()
    if not primer_path.is_file():
        parser.exit(2, f"{parser.prog}: error: primer file not found: {primer_path}\n")

    if args.ephe:
        astro_engine.set_ephe_path(args.ephe)

    try:
        template_chart = hor_parser.load_hor(primer_path)
        zone = resolve_zone(template_chart, args.tz)
        events = scan_asc_changes(
            template_chart,
            args.start_date,
            args.end_date,
            args.window_start,
            args.window_end,
            args.step_min,
            args.tol_min,
            zone,
        )
    except (ValueError, RuntimeError) as exc:
        parser.exit(2, f"{parser.prog}: error: {exc}\n")

    if not args.tz:
        print(
            "Warning: no --tz supplied; using the .hor file's fixed UTC offset. "
            "Use an IANA timezone for scans that may cross a DST transition."
        )

    if not events:
        print("No Ascendant sign changes found in the given window.")
        return 0

    output_path = resolve_output_path(args.out, args.start_date, args.end_date)
    zone_label = args.tz or f"fixed UTC{template_chart.tz_offset_hours:+}"
    header_lines = [
        "# Ascendant Change Reports",
        "",
        f"Primer: {primer_path}",
        f"Date window: {args.start_date} to {args.end_date}",
        f"Daily time window (local): {args.window_start}–{args.window_end}",
        f"Timezone: {zone_label}",
        f"Ephemeris: {args.ephe or 'SWISSEPH_EPHE'}",
        "",
    ]

    sections: list[str] = ["\n".join(header_lines)]
    for dt_utc, asc_idx, asc_lon in events:
        dt_local = dt_utc.astimezone(zone)
        chart = chart_at(template_chart, dt_utc, zone)
        planets = astro_engine.compute_planets(chart)
        houses = astro_engine.compute_houses(chart)
        reports, relationships = build_reports(chart, planets, houses)
        markdown = output.build_markdown_report(
            chart,
            reports,
            houses,
            planets,
            relationships,
            include_almuten=args.verbose,
        )
        header = [
            f"## {SIGNS[asc_idx]} rising — {dt_local.isoformat()} (local) / "
            f"{dt_utc.isoformat()}Z",
            f"- Asc @ {asc_lon:.2f}°",
            "",
        ]
        sections.append("\n".join(header) + "\n" + markdown)

    output_path.write_text("\n\n".join(sections), encoding="utf-8")
    print(f"Wrote {len(events)} reports to {output_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
