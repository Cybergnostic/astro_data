"""Command-line entry point for reading Morinus ``.hor`` files."""

from __future__ import annotations

import argparse
from datetime import timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Sequence

from . import astro_engine, hor_parser, output
from .analysis import build_reports
from .models import ChartInput

DEFAULT_OUTPUT_DIR = Path("outputs")


def _package_version() -> str:
    try:
        return version("hor-tools")
    except PackageNotFoundError:  # pragma: no cover - source-tree fallback
        return "0.1.0"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hor-reader",
        description="Read a Morinus .hor file and render the traditional astrology report.",
    )
    parser.add_argument("hor_file", type=Path, help="Path to a Morinus .hor file.")
    parser.add_argument("--html", metavar="PATH", help="Export a Rich HTML report.")
    parser.add_argument(
        "--md",
        "--markdown",
        dest="md",
        metavar="PATH",
        help="Export a Markdown report.",
    )
    parser.add_argument(
        "--ephe",
        metavar="DIR",
        help="Swiss Ephemeris directory (overrides SWISSEPH_EPHE).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show a full traceback if report generation fails.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_package_version()}")
    return parser


def resolve_output_path(path_str: str | None) -> Path | None:
    """Resolve a requested export path and create its parent directory."""
    if not path_str:
        return None

    path = Path(path_str).expanduser()
    if not path.is_absolute() and path.parent == Path("."):
        path = DEFAULT_OUTPUT_DIR / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _render_report(
    chart: ChartInput,
    html_path: Path | None,
    md_path: Path | None,
) -> None:
    planets = astro_engine.compute_planets(chart)
    houses = astro_engine.compute_houses(chart)
    reports, relationships = build_reports(chart, planets, houses)

    # Rich is a runtime dependency, but keeping the text fallback makes the
    # library usable in constrained environments and preserves old behavior.
    try:
        import rich  # type: ignore  # noqa: F401
    except ModuleNotFoundError:  # pragma: no cover - dependency safety net
        output.print_full_report(chart, reports, houses, relationships)
        if html_path is not None:
            raise RuntimeError("HTML export requires the 'rich' package.")
    else:
        output.print_rich_report(chart, reports, houses, relationships)
        if html_path is not None:
            output.export_rich_html(
                str(html_path), chart, reports, houses, planets, relationships
            )

    if md_path is not None:
        md_content = output.build_markdown_report(
            chart, reports, houses, planets, relationships
        )
        md_path.write_text(md_content, encoding="utf-8")

    print()
    output.print_almuten_tables(chart, planets, houses)


def _scan_helper_template(chart: ChartInput, ephe_path: str | None) -> str:
    dt_utc = chart.datetime_utc
    if dt_utc.tzinfo is not None:
        dt_utc = dt_utc.astimezone(timezone.utc).replace(tzinfo=None)
    dt_str = dt_utc.isoformat() + "Z"

    parts = [
        "hor-scan-events",
        f'--start "{dt_str}"',
        '--end "<END_ISO_UTC>"',
        f"--lat {chart.latitude}",
        f"--lon {chart.longitude}",
    ]
    if ephe_path:
        parts.append(f'--ephe "{Path(ephe_path).expanduser()}"')
    return " ".join(parts)


def run(args: argparse.Namespace) -> int:
    file_path = args.hor_file.expanduser()
    if not file_path.is_file():
        raise FileNotFoundError(f".hor file not found: {file_path}")

    if args.ephe:
        astro_engine.set_ephe_path(args.ephe)

    chart = hor_parser.load_hor(file_path)
    html_path = resolve_output_path(args.html)
    md_path = resolve_output_path(args.md)
    _render_report(chart, html_path, md_path)

    print("\nScan helper template:", _scan_helper_template(chart, args.ephe))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point used by the ``hor-reader`` console script."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return run(args)
    except Exception as exc:
        if args.debug:
            raise
        parser.exit(2, f"{parser.prog}: error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
