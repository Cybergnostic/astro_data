"""Command-line entry point for reading Morinus ``.hor`` files."""

from __future__ import annotations

import argparse
from datetime import timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Sequence

from . import astro_engine, hor_parser, output
from .analysis import build_reports
from .analysis.technical import build_natal_technical_report
from .models import ChartInput
from .rendering.pretty_report import build_pretty_html, build_pretty_markdown
from .rendering.technical import print_terminal_summary

DEFAULT_OUTPUT_DIR = Path("outputs")


def _package_version() -> str:
    try:
        return version("hor-tools")
    except PackageNotFoundError:  # pragma: no cover - source-tree fallback
        return "0.1.0"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hor-reader",
        description=(
            "Read a Morinus .hor file, show the compact traditional-astrology snapshot, "
            "and write polished complete Markdown/HTML technical reports."
        ),
    )
    parser.add_argument("hor_file", type=Path, help="Path to a Morinus .hor file.")
    parser.add_argument(
        "--html",
        metavar="PATH",
        help="Export the complete responsive HTML technical report.",
    )
    markdown = parser.add_mutually_exclusive_group()
    markdown.add_argument(
        "--md",
        "--markdown",
        dest="md",
        metavar="PATH",
        help="Override the default Markdown output path.",
    )
    markdown.add_argument(
        "--no-md",
        action="store_true",
        help="Do not write the automatic complete Markdown report.",
    )
    parser.add_argument(
        "--verbose-terminal",
        action="store_true",
        help="Also print the previous full terminal tables after the compact snapshot.",
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


def _default_markdown_path(hor_file: Path) -> Path:
    path = DEFAULT_OUTPUT_DIR / f"{hor_file.stem}_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _render_report(
    chart: ChartInput,
    html_path: Path | None,
    md_path: Path | None,
    *,
    verbose_terminal: bool,
) -> None:
    planets = astro_engine.compute_planets(chart)
    houses = astro_engine.compute_houses(chart)
    reports, relationships = build_reports(chart, planets, houses)
    technical = build_natal_technical_report(
        chart, planets, houses, reports, relationships
    )

    print_terminal_summary(chart, reports, houses, technical)

    if verbose_terminal:
        print()
        try:
            import rich  # type: ignore  # noqa: F401
        except ModuleNotFoundError:  # pragma: no cover - dependency safety net
            output.print_full_report(chart, reports, houses, relationships)
        else:
            output.print_rich_report(chart, reports, houses, relationships)
        print()
        output.print_almuten_tables(chart, planets, houses)

    legacy: str | None = None
    if html_path is not None or md_path is not None:
        legacy = output.build_markdown_report(
            chart, reports, houses, planets, relationships
        )

    if html_path is not None:
        html_content = build_pretty_html(
            chart, reports, houses, technical, legacy or ""
        )
        html_path.write_text(html_content, encoding="utf-8")
        print(f"\nFull HTML report: {html_path}")

    if md_path is not None:
        md_content = build_pretty_markdown(
            chart, reports, houses, technical, legacy or ""
        )
        md_path.write_text(md_content, encoding="utf-8")
        print(f"\nFull Markdown report: {md_path}")


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
    if args.no_md:
        md_path = None
    elif args.md:
        md_path = resolve_output_path(args.md)
    else:
        md_path = _default_markdown_path(file_path)

    _render_report(
        chart,
        html_path,
        md_path,
        verbose_terminal=args.verbose_terminal,
    )

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
