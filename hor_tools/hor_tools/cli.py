"""Command line entry point for reading Morinus .hor files."""

from __future__ import annotations

import sys
from pathlib import Path

from . import astro_engine, hor_parser, output
from .analysis import build_reports
from .models import ChartInput


def main() -> None:
    """
    CLI entry point.

    Usage:
        hor-reader path/to/file.hor
    """

    html_path = None
    md_path = None
    positional = []
    it = iter(sys.argv[1:])
    for arg in it:
        if arg == "--html":
            try:
                html_path = next(it)
            except StopIteration:
                print("Error: --html requires a path argument")
                sys.exit(1)
        elif arg.startswith("--html="):
            html_path = arg.split("=", 1)[1]
        elif arg == "--md" or arg == "--markdown":
            try:
                md_path = next(it)
            except StopIteration:
                print("Error: --md/--markdown requires a path argument")
                sys.exit(1)
        elif arg.startswith("--md=") or arg.startswith("--markdown="):
            md_path = arg.split("=", 1)[1]
        else:
            positional.append(arg)

    if len(positional) < 1:
        print("Usage: hor-reader [--html out.html] [--md out.md] path/to/file.hor")
        sys.exit(1)

    file_path = Path(positional[0])
    if not file_path.exists():
        print(f"Error: file not found -> {file_path}")
        sys.exit(1)

    try:
        chart: ChartInput = hor_parser.load_hor(file_path)
    except Exception as exc:  # pragma: no cover - CLI defensive path
        print(f"Error parsing .hor file: {exc}")
        raise

    planets = astro_engine.compute_planets(chart)
    houses = astro_engine.compute_houses(chart)
    reports = build_reports(chart, planets, houses)

    # Prefer Rich tables if rich is installed; otherwise fall back to text.
    try:
        import rich  # type: ignore  # noqa: F401
    except ModuleNotFoundError:
        output.print_full_report(reports, houses)
    else:
        output.print_rich_report(reports, houses)
        if html_path:
            output.export_rich_html(html_path, chart, reports, houses, planets)

    if md_path:
        md_content = output.build_markdown_report(chart, reports, houses, planets)
        Path(md_path).write_text(md_content, encoding="utf-8")

    # Always show Almuten tables after main report
    print()
    output.print_almuten_tables(chart, planets, houses)


if __name__ == "__main__":
    main()
