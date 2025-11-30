"""Command line entry point for reading Morinus .hor files."""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import timezone

from . import astro_engine, hor_parser, output
from .analysis import build_reports
from .models import ChartInput

DEFAULT_OUTPUT_DIR = Path("outputs")


def main() -> None:
    """
    CLI entry point.

    Usage:
        hor-reader path/to/file.hor
    """

    html_path = None
    md_path = None
    ephe_path = None
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
        elif arg == "--ephe":
            try:
                ephe_path = next(it)
            except StopIteration:
                print("Error: --ephe requires a path argument")
                sys.exit(1)
        elif arg.startswith("--ephe="):
            ephe_path = arg.split("=", 1)[1]
        else:
            positional.append(arg)

    if len(positional) < 1:
        print("Usage: hor-reader [--html out.html] [--md out.md] [--ephe ephe_dir] path/to/file.hor")
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

    if ephe_path:
        astro_engine.set_ephe_path(str(Path(ephe_path).expanduser()))

    def resolve_output_path(path_str: str | None) -> Path | None:
        if not path_str:
            return None
        p = Path(path_str)
        if not p.is_absolute() and p.parent == Path("."):
            p = DEFAULT_OUTPUT_DIR / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    html_path_resolved = resolve_output_path(html_path)
    md_path_resolved = resolve_output_path(md_path)

    planets = astro_engine.compute_planets(chart)
    houses = astro_engine.compute_houses(chart)
    reports, relationships = build_reports(chart, planets, houses)

    # Prefer Rich tables if rich is installed; otherwise fall back to text.
    try:
        import rich  # type: ignore  # noqa: F401
    except ModuleNotFoundError:
        output.print_full_report(reports, houses, relationships)
    else:
        output.print_rich_report(reports, houses, relationships)
        if html_path_resolved:
            output.export_rich_html(str(html_path_resolved), chart, reports, houses, planets, relationships)

    if md_path_resolved:
        md_content = output.build_markdown_report(chart, reports, houses, planets, relationships)
        md_path_resolved.write_text(md_content, encoding="utf-8")

    # Always show Almuten tables after main report
    print()
    output.print_almuten_tables(chart, planets, houses)

    # Offer a ready-to-edit scan_events.py command with chart location prefilled.
    dt_utc = chart.datetime_utc
    if dt_utc.tzinfo is not None:
        dt_utc = dt_utc.astimezone(timezone.utc).replace(tzinfo=None)
    dt_str = dt_utc.isoformat() + "Z"
    scan_cmd_parts = [
        "python",
        "scan_events.py",
        f'--start "{dt_str}"',
        '--end "<END_ISO_UTC>"',
        f"--lat {chart.latitude}",
        f"--lon {chart.longitude}",
    ]
    if ephe_path:
        scan_cmd_parts.append(f'--ephe "{Path(ephe_path).expanduser()}"')
    print("\nScan helper template:", " ".join(scan_cmd_parts))


if __name__ == "__main__":
    main()
