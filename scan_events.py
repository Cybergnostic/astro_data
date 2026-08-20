#!/usr/bin/env python3
"""Backward-compatible wrapper for :mod:`hor_tools.commands.scan_events`."""

from hor_tools.commands.scan_events import (
    DEFAULT_ASPECTS,
    SIGNS,
    _crossed_aspect_target,
    _unwrap_near,
    angle_between,
    aspect_separation,
    build_parser,
    chart_for,
    directed_angle,
    main,
    normalize_angle,
    parse_aspects,
    parse_dt,
    positions_at,
    refine_aspect,
    refine_ingress,
    scan_range,
    shortest_angle,
)

__all__ = [
    "DEFAULT_ASPECTS",
    "SIGNS",
    "_crossed_aspect_target",
    "_unwrap_near",
    "angle_between",
    "aspect_separation",
    "build_parser",
    "chart_for",
    "directed_angle",
    "main",
    "normalize_angle",
    "parse_aspects",
    "parse_dt",
    "positions_at",
    "refine_aspect",
    "refine_ingress",
    "scan_range",
    "shortest_angle",
]


if __name__ == "__main__":
    raise SystemExit(main())
