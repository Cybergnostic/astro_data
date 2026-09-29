"""Generate a complete natal report from normalized chart data.

This is the non-Morinus input adapter used by integrations such as Hint Client
Context. It deliberately feeds the same ChartInput/reporting pipeline as
hor-reader rather than duplicating astrological logic.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .. import astro_engine
from ..cli import _render_report
from ..models import ChartInput


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from exc


def _parse_time(value: str) -> time:
    try:
        return time.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("time must be HH:MM or HH:MM:SS") from exc


def _resolve_output(path_value: str) -> Path:
    path = Path(path_value).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def build_chart(
    *,
    name: str,
    local_date: date,
    local_time: time,
    timezone_name: str,
    latitude: float,
    longitude: float,
    location_name: str | None,
    sex: str,
) -> ChartInput:
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"unknown IANA timezone: {timezone_name}") from exc

    naive = datetime.combine(local_date, local_time)
    fold0 = naive.replace(tzinfo=zone, fold=0)
    fold1 = naive.replace(tzinfo=zone, fold=1)
    if fold0.utcoffset() != fold1.utcoffset():
        raise ValueError(
            f"local time {naive.isoformat()} falls in a timezone transition in {timezone_name}"
        )

    offset = fold0.utcoffset()
    if offset is None:
        raise ValueError(f"could not determine UTC offset for {timezone_name}")
    tz_offset_hours = offset.total_seconds() / 3600.0

    male: bool | None
    if sex == "male":
        male = True
    elif sex == "female":
        male = False
    else:
        male = None

    return ChartInput(
        name=name,
        datetime_utc=fold0.astimezone(timezone.utc),
        tz_offset_hours=tz_offset_hours,
        latitude=latitude,
        longitude=longitude,
        house_system="W",
        zodiac="T",
        location_name=location_name,
        altitude_m=None,
        male=male,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hor-report",
        description=(
            "Generate the complete Traditional Astrology report from normalized "
            "date/time/place data instead of a Morinus .hor file."
        ),
    )
    parser.add_argument("--name", required=True)
    parser.add_argument("--date", required=True, type=_parse_date, help="YYYY-MM-DD")
    parser.add_argument("--time", required=True, type=_parse_time, help="HH:MM or HH:MM:SS")
    parser.add_argument("--tz", required=True, help="IANA timezone, e.g. Europe/Belgrade")
    parser.add_argument("--lat", required=True, type=float)
    parser.add_argument("--lon", required=True, type=float)
    parser.add_argument("--location", default=None)
    parser.add_argument("--sex", choices=("male", "female", "unknown"), default="unknown")
    parser.add_argument("--md", required=True, help="Markdown output path")
    parser.add_argument("--html", required=True, help="HTML output path")
    parser.add_argument("--ephe", metavar="DIR", help="Swiss Ephemeris directory")
    parser.add_argument("--verbose-terminal", action="store_true")
    return parser


def run(args: argparse.Namespace) -> int:
    if args.ephe:
        astro_engine.set_ephe_path(args.ephe)

    chart = build_chart(
        name=args.name,
        local_date=args.date,
        local_time=args.time,
        timezone_name=args.tz,
        latitude=args.lat,
        longitude=args.lon,
        location_name=args.location,
        sex=args.sex,
    )
    _render_report(
        chart,
        _resolve_output(args.html),
        _resolve_output(args.md),
        verbose_terminal=args.verbose_terminal,
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except Exception as exc:
        parser.exit(2, f"{parser.prog}: error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
