#!/usr/bin/env python3
"""Backward-compatible wrapper for :mod:`hor_tools.commands.asc_window`."""

from hor_tools.commands.asc_window import (
    DEFAULT_OUTPUT_DIR,
    SIGNS,
    _fixed_template_zone,
    asc_sign_at,
    build_parser,
    chart_at,
    daterange,
    main,
    offset_hours_at,
    parse_date,
    parse_time,
    refine_asc_change,
    resolve_output_path,
    resolve_zone,
    scan_asc_changes,
    to_utc_local,
)

__all__ = [
    "DEFAULT_OUTPUT_DIR",
    "SIGNS",
    "_fixed_template_zone",
    "asc_sign_at",
    "build_parser",
    "chart_at",
    "daterange",
    "main",
    "offset_hours_at",
    "parse_date",
    "parse_time",
    "refine_asc_change",
    "resolve_output_path",
    "resolve_zone",
    "scan_asc_changes",
    "to_utc_local",
]


if __name__ == "__main__":
    raise SystemExit(main())
