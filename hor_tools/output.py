"""Output helpers for presenting computed chart data."""

from __future__ import annotations

from datetime import timedelta
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from .rendering.almuten import print_almuten_tables
from .rendering.relationships import render_relationship_tables as _render_relationship_tables
from .models import AspectInfo, ChartInput, ChartRelationships, Houses, PlanetPosition, PlanetReport, ReflectionHit
from .analysis.dignity import SIGNS, degree_in_sign

# Optional: maps for pretty symbols when rendering with Rich
PLANET_SYMBOLS = {
    "Sun": "☉",
    "Moon": "☽",
    "Mercury": "☿",
    "Venus": "♀",
    "Mars": "♂",
    "Jupiter": "♃",
    "Saturn": "♄",
}

SIGN_SYMBOLS = {
    "Aries": "♈",
    "Taurus": "♉",
    "Gemini": "♊",
    "Cancer": "♋",
    "Leo": "♌",
    "Virgo": "♍",
    "Libra": "♎",
    "Scorpio": "♏",
    "Sagittarius": "♐",
    "Capricorn": "♑",
    "Aquarius": "♒",
    "Pisces": "♓",
}


def _format_coord(value: float, positive_label: str, negative_label: str, precision: int = 4) -> str:
    """Return a signed coordinate with cardinal direction."""

    hemi = positive_label if value >= 0 else negative_label
    return f"{abs(value):.{precision}f}° {hemi}"


def _tz_offset_str(offset_hours: float) -> str:
    """Format timezone offset hours as UTC±HH:MM."""

    sign = "+" if offset_hours >= 0 else "-"
    hours = int(abs(offset_hours))
    minutes = int(round((abs(offset_hours) - hours) * 60))
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def _chart_header_lines(chart: ChartInput) -> list[str]:
    """Human-readable chart basics for the top of the report."""

    offset = chart.tz_offset_hours
    local_dt = chart.datetime_utc + timedelta(hours=offset)
    offset_str = _tz_offset_str(offset)
    lat_str = _format_coord(chart.latitude, "N", "S")
    lon_str = _format_coord(chart.longitude, "E", "W")
    house_sys = "Whole sign" if chart.house_system == "W" else chart.house_system
    zodiac = "Tropical" if chart.zodiac == "T" else chart.zodiac
    return [
        f"Chart: {chart.name}",
        f"Local: {local_dt.strftime('%Y-%m-%d %H:%M:%S')} ({offset_str})",
        f"UTC:   {chart.datetime_utc.strftime('%Y-%m-%d %H:%M:%S')} (UTC)",
        f"Location: {lat_str}, {lon_str}",
        f"House system: {house_sys} | Zodiac: {zodiac}",
    ]


def _build_dignity_lines(rep: PlanetReport, markup: bool = False) -> list[str]:
    """
    Build dignity lines in a consistent order for tabular display.

    Always emit the same six slots: ruler, exalt, trip, term, face, debility.
    """

    def fmt(label: str, value: str | None, emphasize: bool = False) -> str:
        missing = value is None
        txt = f"{label} {value if value else '-'}"
        if not markup:
            return txt
        if missing:
            return f"[dim]{txt}[/]"
        if emphasize:
            return f"[bold green]{txt.upper()}[/]"
        return txt

    lines: list[str] = []
    lines.append(fmt("ruler", rep.ruler, emphasize=rep.is_domicile))
    lines.append(fmt("exalt", rep.exaltation_lord, emphasize=rep.is_exalted))
    lines.append(fmt("trip", rep.triplicity_lord))
    lines.append(fmt("term", rep.term_lord))
    lines.append(fmt("face", rep.face_lord))

    if rep.is_detriment or rep.is_fall:
        deb = []
        if rep.is_detriment:
            deb.append("[bold red]DETRIMENT[/]" if markup else "detriment")
        if rep.is_fall:
            deb.append("[bold red]FALL[/]" if markup else "fall")
        lines.append("; ".join(deb))
    else:
        lines.append("[dim]no debility[/]" if markup else "no debility")

    return lines


def _build_sect_lines(rep: PlanetReport, markup: bool = False) -> list[str]:
    """Return sect/condition lines with stronger emphasis for positive conditions."""

    def pale(text: str) -> str:
        return f"[dim]{text}[/]" if markup else text

    def strong(text: str, color: str) -> str:
        return f"[bold {color}]{text.upper()}[/]" if markup else text

    lines: list[str] = []
    lines.append(pale(f"{rep.sect_chart} chart"))
    lines.append(pale(f"{rep.sect_planet} planet"))

    if rep.in_sect:
        lines.append(strong("in sect", "green"))
    else:
        lines.append(pale("out of sect"))

    if rep.hayz:
        lines.append(strong("hayz", "gold1"))
    else:
        lines.append(pale("no hayz"))

    if rep.halb:
        lines.append(strong("halb", "cyan"))
    else:
        lines.append(pale("no halb"))

    if rep.planet.name != "Sun":
        orient = "oriental" if rep.oriental else "occidental"
        color = "magenta" if rep.oriental else "blue"
        lines.append(f"[{color}]{orient}[/]" if markup else orient)

    return lines


def _build_motion_lines(rep: PlanetReport, markup: bool = False) -> list[str]:
    """Return motion lines with emphasis for retrograde/slow/latitudes."""

    def strong(text: str, color: str) -> str:
        return f"[bold {color}]{text}[/]" if markup else text

    def pale(text: str) -> str:
        return f"[dim]{text}[/]" if markup else text

    p = rep.planet
    direction = strong("retrograde", "red") if p.retrograde else pale("direct")
    lines = [direction]
    if rep.is_true_cazimi:
        lines.insert(0, strong("TRUE CAZIMI (lon+lat)", "magenta"))
    elif rep.is_cazimi:
        lines.insert(0, strong("CAZIMI (longitude)", "magenta"))

    speed_class = rep.speed_class
    if speed_class.lower() in {"slow", "swift"}:
        lines.append(strong(speed_class, "red" if speed_class == "slow" else "green"))
    else:
        lines.append(pale(speed_class))

    lines.append(f"{abs(p.speed_long):.2f}°/day")
    lines.append(f"{rep.speed_ratio:.2f}x mean")
    lines.append(f"latitude {p.latitude:+.2f}°")
    return lines


def _build_condition_lines(rep: PlanetReport, markup: bool = False) -> list[str]:
    """Render source-backed accidental testimonies kept outside aggregate scores."""

    def styled(text: str, color: str) -> str:
        return f"[bold {color}]{text}[/]" if markup else text

    def pale(text: str) -> str:
        return f"[dim]{text}[/]" if markup else text

    lines: list[str] = []
    if rep.is_in_planetary_joy:
        lines.append(styled("planetary joy", "green"))

    if rep.latitude_condition == "north_strengthening":
        lines.append(styled("north latitude: strengthening", "green"))
    elif rep.latitude_condition == "south_weakening":
        lines.append(styled("south latitude: weakening", "red"))
    else:
        lines.append(pale("on ecliptic"))

    if rep.is_in_via_combusta:
        lines.append(styled("via combusta (19 Libra-3 Scorpio)", "red"))
    if rep.is_void_of_course:
        lines.append(styled("VOID OF COURSE", "yellow"))

    return lines


def _format_synodic(rep: PlanetReport, markup: bool = False) -> str:
    """Return a short synodic phase string if available."""
    phase = rep.planet.synodic_phase
    if not phase:
        return ""
    phase_cazimi = "cazimi" in (phase.code or "")
    if rep.is_true_cazimi:
        label = "True cazimi"
        is_cazimi = True
    elif rep.is_cazimi or phase_cazimi:
        label = "Cazimi"
        is_cazimi = True
    else:
        label = phase.label
        is_cazimi = False
    if markup and is_cazimi:
        label = f"[bold magenta]{label.upper()}[/]"
    elif not markup and is_cazimi:
        label = label.upper()
    return f"{label} ({phase.group})"


def _format_aspect_type(raw: str) -> str:
    """Color applying vs separating aspects."""
    if "applying" in raw:
        return f"[bold green]{raw}[/]"
    return f"[dim]{raw}[/]"


def _format_reflection_line(label: str, target_longitude: float, hits: list[ReflectionHit]) -> str:
    """Build a concise antiscia/contra-antiscia line for text output."""
    target = _format_long_with_sign(target_longitude)
    if not hits:
        return f"{label}: {target} (degree-sum rule, no contacts)"
    hit_bits = ", ".join(f"{hit.other} (Δ {hit.orb:.2f}°)" for hit in hits)
    return f"{label}: {target} -> {hit_bits} [deg sum 29]"


def _format_domicile_lines(rep: PlanetReport, markup: bool = False) -> list[str]:
    """Return aversion/witness lines for each domicile."""

    def style(text: str, color: str) -> str:
        return f"[bold {color}]{text}[/]" if markup else text

    lines: list[str] = []
    for dom in rep.domicile_aversions:
        status: str
        if dom.sees:
            status = style("witnesses domicile", "green")
        elif dom.avoided:
            status = style("aversion avoided", "yellow")
        else:
            status = style("in aversion", "red")

        details = []
        if dom.occupants:
            details.append(f"occupants: {', '.join(dom.occupants)}")
        if dom.avoided_by:
            details.extend(dom.avoided_by)
        detail_txt = f" ({'; '.join(details)})" if details else ""
        lines.append(f"{dom.domicile_sign}: {status}{detail_txt}")
    return lines


def _house_style(house_num: int) -> str:
    """Return a style for houses: angular, succedent, cadent."""
    if house_num in {1, 4, 7, 10}:
        return "bold white"
    if house_num in {2, 5, 8, 11}:
        return "cyan"
    return "dim"


def _planet_label(name: str) -> str:
    """Return a planet label (use plain names for readability)."""
    return name


def _sign_label(sign: str, use_symbol: bool = True) -> str:
    """Return a sign label, optionally prefixed with its symbol."""
    if not use_symbol:
        return sign
    symbol = SIGN_SYMBOLS.get(sign)
    return f"{symbol} {sign}" if symbol else sign


def _format_position(p: PlanetPosition, sign_name: str, use_symbol: bool = True) -> str:
    """Return a compact position string with degrees and sign symbol."""
    deg_in_sign = degree_in_sign(p.longitude)
    deg = int(deg_in_sign)
    minutes = int(round((deg_in_sign - deg) * 60))
    # Add a trailing space to keep the Rich table column width stable in HTML export.
    return f"{deg:02d}°{minutes:02d}' {_sign_label(sign_name, use_symbol)} "


def _unique_aspects(reports: list[PlanetReport]) -> list[tuple[str, AspectInfo]]:
    """
    Collect aspects as unique pairs (to avoid duplicates for A-B and B-A).
    Returns list of (planet_name, aspect_info) sorted by orb ascending.
    """
    seen = set()
    collected: list[tuple[str, AspectInfo]] = []
    for rep in reports:
        for asp in rep.aspects:
            key = tuple(sorted((rep.planet.name, asp.other))) + (asp.kind,)
            if key in seen:
                continue
            seen.add(key)
            collected.append((rep.planet.name, asp))
    collected.sort(key=lambda item: item[1].orb)
    return collected


def _collect_reflections(reports: list[PlanetReport]) -> list[tuple[str, str, float, ReflectionHit]]:
    """Collect antiscia/contra-antiscia hits sorted by orb."""
    rows: list[tuple[str, str, float, ReflectionHit]] = []
    for rep in reports:
        rows.extend((rep.planet.name, "antiscia", rep.antiscia_longitude, hit) for hit in rep.antiscia_hits)
        rows.extend(
            (rep.planet.name, "contra-antiscia", rep.contra_antiscia_longitude, hit) for hit in rep.contra_antiscia_hits
        )
    rows.sort(key=lambda row: row[3].orb)
    return rows


def _collect_domicile_aversion(reports: list[PlanetReport]) -> list[tuple[str, str, str, str]]:
    """
    Return rows for the domicile aversion table.

    Subsequent domiciles of the same planet get an empty planet label so the table
    does not visually repeat the planet name on every line.
    """
    rows: list[tuple[str, str, str, str]] = []
    for rep in reports:
        for idx, dom in enumerate(rep.domicile_aversions):
            if dom.sees:
                status = "[green]witnesses[/]"
            elif dom.avoided:
                status = "[yellow]aversion avoided[/]"
            else:
                status = "[red]in aversion[/]"
            details = []
            if dom.occupants:
                details.append(f"occupants: {', '.join(dom.occupants)}")
            if dom.avoided_by:
                details.append("; ".join(dom.avoided_by))
            detail_txt = "; ".join(details) if details else "—"
            planet_label = rep.planet.name if idx == 0 else ""
            rows.append((planet_label, dom.domicile_sign, status, detail_txt))
    return rows


def print_text(planets: list[PlanetPosition], houses: Houses) -> None:
    """
    Print a simple text summary of planetary positions and Houses:
    - one line per planet: "Sun  15°23' Leo  (House 7)"
    - then a list of Whole sign House cusps.
    """

    # Planets
    for pos in planets:
        sign = SIGNS[int(pos.longitude // 30) % 12]
        deg_in_sign, minutes = _format_degrees(pos.longitude)
        print(f"{pos.name:<8} {deg_in_sign:02d}°{minutes:02d}' {sign:<11} (House {pos.house})")

    # House cusps (1 - 12), without trying to label 10 as MC
    print("\nHouses (Whole sign cusps):")
    for idx in range(1, 13):
        cusp_long = houses.cusps[idx]
        sign = SIGNS[int(cusp_long // 30) % 12]
        deg_in_sign, minutes = _format_degrees(cusp_long)
        label = f"{idx:02d}"
        print(f"House {label} {deg_in_sign:02d}°{minutes:02d}' {sign}")

    # Nicely formatted Ascendant and MC
    print(f"\nAscendant: {_format_long_with_sign(houses.asc)}")
    if houses.mc is not None:
        print(f"MC:        {_format_long_with_sign(houses.mc)}")


def print_full_report(
    chart: ChartInput, reports: list[PlanetReport], houses: Houses, relationships: ChartRelationships | None = None
) -> None:
    """
    Print a detailed traditional report for each planet,
    including dignities, sect/hayz/halb, motion, fixed stars, and aspects.
    """

    header = _chart_header_lines(chart)
    for line in header:
        print(line)
    print()

    for rep in reports:
        p = rep.planet
        sign_name = rep.sign
        deg_in_sign = degree_in_sign(p.longitude)
        deg = int(deg_in_sign)
        minutes = int(round((deg_in_sign - deg) * 60))

        print(f"{p.name} {deg:02d}°{minutes:02d}' {sign_name} (House {p.house})")

        dignity_lines = _build_dignity_lines(rep)
        print("  Dignity:")
        for ln in dignity_lines:
            print(f"    {ln}")

        sect_lines = _build_sect_lines(rep)
        print("  Sect:")
        for ln in sect_lines:
            print(f"    {ln}")

        motion_lines = _build_motion_lines(rep)
        print("  Motion:")
        for ln in motion_lines:
            print(f"    {ln}")

        condition_lines = _build_condition_lines(rep)
        if condition_lines:
            print("  Conditions:")
            for ln in condition_lines:
                print(f"    {ln}")

        synodic_str = _format_synodic(rep, markup=False)
        if synodic_str:
            print(f"  Synodic: {synodic_str}")

        if rep.fixed_stars:
            stars = ", ".join(rep.fixed_stars)
            print(f"  Fixed stars (course orb): {stars}")
        else:
            print("  Fixed stars (course orb): none")

        if rep.aspects:
            print("  Aspects:")
            for a in rep.aspects:
                applying_sep = "applying" if a.applying else "separating"
                dexter_sin = "dexter" if a.dexter else "sinister"
                mutual = ""
                if a.mutual_application:
                    mutual = " [mutual application]"
                elif a.mutual_separation:
                    mutual = " [mutual separation]"
                counter = " [counter-ray]" if a.counter_ray else ""
                print(
                    f"    - {a.kind.capitalize()} {a.other} "
                    f"(orb {a.orb:.2f}°, {applying_sep}, {dexter_sin}){mutual}{counter}"
                )
        else:
            print("  Aspects: none")

        print(f"  {_format_reflection_line('Antiscia', rep.antiscia_longitude, rep.antiscia_hits)}")
        print(f"  {_format_reflection_line('Contra-antiscia', rep.contra_antiscia_longitude, rep.contra_antiscia_hits)}")

        dom_lines = _format_domicile_lines(rep, markup=False)
        if dom_lines:
            print("  Domicile sight:")
            for ln in dom_lines:
                print(f"    {ln}")

        if rep.is_bonified or rep.is_maltreated:
            if rep.is_bonified:
                sources = "; ".join(f"{src.reason} ({src.planet})" for src in rep.bonification_sources)
                print(f"  Bonification: {sources}")
            if rep.is_maltreated:
                sources = "; ".join(f"{src.reason} ({src.planet})" for src in rep.maltreatment_sources)
                print(f"  Maltreatment: {sources}")

        if rep.is_feral:
            print("  Feral: no whole-sign aspects")

        if rep.receptions_given or rep.receptions_received or rep.generosities_given or rep.generosities_received:
            if rep.receptions_given:
                rows = ", ".join(
                    f"{r.guest} ({'/'.join(r.dignities)}){f' via {r.aspect_kind}' if r.aspect_kind else ''}"
                    for r in rep.receptions_given
                )
                print(f"  Reception given: {rows}")
            if rep.receptions_received:
                rows = ", ".join(
                    f"{r.host} ({'/'.join(r.dignities)}){f' via {r.aspect_kind}' if r.aspect_kind else ''}"
                    for r in rep.receptions_received
                )
                print(f"  Reception received: {rows}")
            if rep.generosities_given:
                rows = ", ".join(
                    f"{r.guest} ({'/'.join(r.dignities)})" for r in rep.generosities_given
                )
                print(f"  Generosity given: {rows}")
            if rep.generosities_received:
                rows = ", ".join(
                    f"{r.host} ({'/'.join(r.dignities)})" for r in rep.generosities_received
                )
                print(f"  Generosity received: {rows}")

        print()

    if relationships:
        print("Domination / Decimation:")
        if relationships.dominations:
            for dom in relationships.dominations:
                counter = " with counter-ray" if dom.has_counter_ray else ""
                print(f"  - {dom.dominator} dominates {dom.dominated} ({dom.relationship}){counter}")
        else:
            print("  none")
        print("\nTranslation of light:")
        if relationships.translations:
            for t in relationships.translations:
                print(
                    f"  - {t.translator} carries light from {t.from_planet} to {t.to_planet} "
                    f"({t.aspect_from.kind} -> {t.aspect_to.kind})"
                )
        else:
            print("  none")
        print("\nCollection of light:")
        if relationships.collections:
            for c in relationships.collections:
                print(
                    f"  - {c.collector} collects from {c.from_planets[0]} and {c.from_planets[1]} "
                    f"({c.aspect_from_first.kind} / {c.aspect_from_second.kind})"
                )
        else:
            print("  none")
        print()

    # Also print Asc and MC nicely like before
    print()
    print("Houses (Whole sign cusps):")
    for i in range(1, 13):
        cusp_long = houses.cusps[i]
        sign = SIGNS[int(cusp_long // 30) % 12]
        deg_in_sign = degree_in_sign(cusp_long)
        d = int(deg_in_sign)
        m = int(round((deg_in_sign - d) * 60))
        print(f"  House {i:02d} {d:02d}°{m:02d}' {sign}")

    print()
    print(f"Ascendant: {houses.asc:.2f}°")
    if houses.mc is not None:
        print(f"MC:        {houses.mc:.2f}°")


def build_markdown_report(
    chart: ChartInput,
    reports: list[PlanetReport],
    houses: Houses,
    planets: list[PlanetPosition],
    relationships: ChartRelationships | None = None,
    include_almuten: bool = True,
) -> str:
    """
    Return a markdown string mirroring the Rich console output.

    By default includes Almuten tables; set include_almuten=False for a lighter report.
    """

    try:
        from rich.console import Console
        from rich.theme import Theme
    except ModuleNotFoundError:
        return _build_text_markdown(chart, reports, houses, planets, relationships, include_almuten)

    console = Console(record=True, theme=Theme({}))
    _render_rich_report(console, chart, reports, houses, relationships, use_sign_symbols=False, use_narrow_icons=True)
    if include_almuten:
        console.print()  # spacer before Almuten section
        print_almuten_tables(chart, planets, houses, console=console)
    text = console.export_text()
    return "```\n" + text.rstrip() + "\n```"


def _build_text_markdown(
    chart: ChartInput,
    reports: list[PlanetReport],
    houses: Houses,
    planets: list[PlanetPosition],
    relationships: ChartRelationships | None = None,
    include_almuten: bool = True,
) -> str:
    """
    Fallback markdown when Rich is unavailable; mirrors the plain console output.
    """

    buf = StringIO()
    with redirect_stdout(buf):
        print_full_report(chart, reports, houses, relationships)
        if include_almuten:
            print()
            print_almuten_tables(chart, planets, houses)
    return "```\n" + buf.getvalue().rstrip() + "\n```"


def print_rich_report(
    chart: ChartInput, reports: list[PlanetReport], houses: Houses, relationships: ChartRelationships | None = None
) -> None:
    """
    Render a rich-styled report with tables for planets, houses, and aspects.
    Requires the 'rich' library; falls back with a helpful error if missing.
    """

    try:
        from rich.console import Console
    except ModuleNotFoundError:
        print("Rich is not installed. Install with 'uv add rich' to use print_rich_report.")
        return

    console = Console()
    _render_rich_report(
        console, chart, reports, houses, relationships, use_sign_symbols=True, use_narrow_icons=False
    )


def export_rich_html(
    path: str | Path,
    chart: ChartInput,
    reports: list[PlanetReport],
    houses: Houses,
    planets: list[PlanetPosition],
    relationships: ChartRelationships | None = None,
) -> None:
    """
    Export the rich report (including Almuten tables) to an HTML file with a dark theme.
    """
    try:
        from rich.console import Console
        from rich.theme import Theme
    except ModuleNotFoundError:
        raise RuntimeError("Rich is not installed. Install with 'uv add rich' to export HTML.") from None

    # Use a neutral theme; we'll inject our own dark background CSS.
    console = Console(record=True, theme=Theme({}))
    # Avoid sign symbols in HTML export so all glyphs share a fixed width.
    _render_rich_report(
        console, chart, reports, houses, relationships, use_sign_symbols=False, use_narrow_icons=True
    )
    console.print()  # spacer before Almuten section
    print_almuten_tables(chart, planets, houses, console=console)
    html = console.export_html(inline_styles=True)
    dark_css = """
<style>
html, body { background:#0b0b0b !important; color:#eaeaea !important; }
pre, code {
  background:#0b0b0b !important;
  color:#eaeaea !important;
  white-space: pre;
  font-family:'Noto Sans Mono','DejaVu Sans Mono','JetBrains Mono','Fira Code','Menlo','Consolas','Courier New',monospace;
  font-variant-ligatures: none;
}
pre code span { white-space: pre; font-family: inherit; }
</style>
""".strip()
    if "</head>" in html:
        html = html.replace("</head>", f"{dark_css}\n</head>", 1)
    else:
        html = f"{dark_css}\n{html}"
    Path(path).write_text(html, encoding="utf-8")


def _render_rich_report(
    console,
    chart: ChartInput,
    reports: list[PlanetReport],
    houses: Houses,
    relationships: ChartRelationships | None,
    use_sign_symbols: bool = True,
    use_narrow_icons: bool = False,
) -> None:
    """Shared rich rendering so we can also export to HTML."""
    from rich import box
    from rich.table import Table
    from rich.text import Text

    header_lines = _chart_header_lines(chart)
    console.print(f"[bold cyan]{header_lines[0]}[/]")
    for line in header_lines[1:]:
        console.print(line)
    console.print()

    # Planetary State table
    planet_table = Table(title="Planetary State", box=box.ROUNDED, expand=False, width=128, padding=(0, 1))
    planet_table.add_column("Planet", style="cyan", no_wrap=True)
    planet_table.add_column("Position", style="magenta", no_wrap=True, justify="right")
    planet_table.add_column("House", justify="center", no_wrap=True)
    planet_table.add_column("Dignity", style="green", overflow="fold", max_width=24)
    planet_table.add_column("Sect", style="yellow", overflow="fold", max_width=22)
    planet_table.add_column("Motion", justify="right", overflow="fold", max_width=22)
    planet_table.add_column("Conditions", style="white", overflow="fold", max_width=28)
    planet_table.add_column("Synodic", style="cyan", overflow="fold", max_width=20)

    for idx, rep in enumerate(reports):
        p = rep.planet
        pos_str = _format_position(p, rep.sign, use_sign_symbols)
        planet_label = _planet_label(p.name)

        dignity_lines = _build_dignity_lines(rep, markup=True)
        sect_lines = _build_sect_lines(rep, markup=True)
        motion_lines = _build_motion_lines(rep, markup=True)
        condition_lines = _build_condition_lines(rep, markup=True)
        synodic = _format_synodic(rep, markup=True)

        # Highlight retrograde in motion
        motion_text = Text.from_markup("\n".join(motion_lines))
        conditions_text = Text.from_markup("\n".join(condition_lines))

        # Apply markup for dignity/sect
        dignity_text = Text.from_markup("\n".join(dignity_lines))
        sect_text = Text.from_markup("\n".join(sect_lines))

        planet_table.add_row(
            planet_label,
            pos_str,
            str(p.house),
            dignity_text,
            sect_text,
            motion_text,
            conditions_text,
            synodic,
        )
        # Spacer row between planets for readability
        if idx < len(reports) - 1:
            planet_table.add_row(*([""] * 8))

    console.print(planet_table)
    console.print()

    # Aspects table (unique pairs)
    aspects = _unique_aspects(reports)
    aspect_table = Table(
        title="Aspects (by orb)",
        box=box.SIMPLE,
        expand=False,
        width=110,
        padding=(0, 1),
    )
    aspect_table.add_column("Pair", style="cyan", overflow="fold", max_width=36)
    aspect_table.add_column("Aspect", justify="center", no_wrap=True)
    aspect_table.add_column("Orb", justify="right", style="green", no_wrap=True)
    aspect_table.add_column("Status", style="yellow", overflow="fold", max_width=20)
    aspect_table.add_column("Polarity", style="magenta", overflow="fold", max_width=12)

    if aspects:
        for src, asp in aspects:
            pair_label = f"{_planet_label(src)} - {_planet_label(asp.other)}"
            aspect_name = asp.kind.capitalize()
            orb_str = f"{asp.orb:.2f}°"

            # Style tight orbs
            orb_text = Text(orb_str)
            if asp.orb < 1.0:
                orb_text.stylize("bold white on red")

            status = "[bold green]applying[/]" if asp.applying else "[dim]separating[/]"
            polarity = "[cyan]dexter[/]" if asp.dexter else "[magenta]sinister[/]"

            mutual = "mutual" if asp.mutual_application else ("mutual sep" if asp.mutual_separation else "")
            counter = "counter-ray" if asp.counter_ray else ""
            extra = ", ".join([p for p in [mutual, counter] if p])
            aspect_table.add_row(
                pair_label,
                aspect_name,
                orb_text,
                Text.from_markup(status if not extra else f"{status} [{extra}]"),
                Text.from_markup(polarity),
            )
    else:
        aspect_table.add_row("—", "None", "—", "—", "—")

    console.print(aspect_table)
    console.print()

    reflections = _collect_reflections(reports)
    reflection_table = Table(
        title="Antiscia / Contra-antiscia",
        box=box.SIMPLE,
        expand=False,
        width=110,
        padding=(0, 1),
    )
    reflection_table.add_column("From", style="cyan", no_wrap=True)
    reflection_table.add_column("Type", style="magenta", no_wrap=True)
    reflection_table.add_column("Target", style="yellow", no_wrap=True)
    reflection_table.add_column("Contact", style="green", overflow="fold", max_width=38)
    reflection_table.add_column("Δ (deg)", justify="right", style="white", no_wrap=True)

    report_map = {rep.planet.name: rep for rep in reports}
    if reflections:
        for src, kind, target_long, hit in reflections:
            target = _format_long_with_sign(target_long)
            other_rep = report_map.get(hit.other)
            if other_rep:
                other_pos = _format_position(other_rep.planet, other_rep.sign, use_sign_symbols).strip()
                contact = f"{hit.other} @ {other_pos}"
            else:
                contact = hit.other
            kind_label = "Antiscia" if kind == "antiscia" else "Contra-antiscia"
            orb_text = Text(f"{hit.orb:.2f}°")
            if hit.orb < 1.0:
                orb_text.stylize("bold white on red")
            reflection_table.add_row(src, kind_label, target, contact, orb_text)
    else:
        reflection_table.add_row("—", "—", "—", "—", "—")

    console.print(reflection_table)
    console.print()

    domicile_rows = _collect_domicile_aversion(reports)
    domicile_table = Table(
        title="Domicile Sight / Aversion",
        box=box.MINIMAL_DOUBLE_HEAD,
        expand=False,
        width=110,
        padding=(0, 1),
    )
    domicile_table.add_column("Planet", style="cyan", no_wrap=True)
    domicile_table.add_column("Domicile", style="magenta", no_wrap=True)
    domicile_table.add_column("Status", style="yellow", no_wrap=True)
    domicile_table.add_column("Details", style="green", overflow="fold", max_width=60)

    if domicile_rows:
        for planet, domicile, status, detail in domicile_rows:
            domicile_table.add_row(planet, domicile, status, detail)
    else:
        domicile_table.add_row("—", "—", "—", "—")

    console.print(domicile_table)
    console.print()

    if relationships:
        _render_relationship_tables(console, reports, relationships, use_narrow_icons=use_narrow_icons)

    # Houses table
    from rich import box as rich_box

    house_table = Table(
        title="Houses (Whole sign)",
        box=rich_box.MINIMAL_DOUBLE_HEAD,
        expand=False,
        width=36,
        padding=(0, 1),
    )
    house_table.add_column("House", justify="center", no_wrap=True)
    house_table.add_column("Sign", style="magenta", no_wrap=True)

    for i in range(1, 13):
        sign = SIGNS[int(houses.cusps[i] // 30) % 12]
        house_table.add_row(f"{i:02d}", _sign_label(sign, use_sign_symbols), style=_house_style(i))

    console.print(house_table)

    angle_table = Table(title="Angles", box=rich_box.MINIMAL, expand=False, width=36, padding=(0, 1))
    angle_table.add_column("Point", justify="center", no_wrap=True)
    angle_table.add_column("Position", style="cyan", no_wrap=True)
    angle_table.add_row("Asc", _format_long_with_sign(houses.asc))
    if houses.mc is not None:
        angle_table.add_row("MC", _format_long_with_sign(houses.mc))
    console.print(angle_table)


def _format_long_with_sign(longitude: float) -> str:
    """Return e.g. '23°29' Capricorn' for a raw longitude."""
    sign = SIGNS[int(longitude // 30) % 12]
    deg, minutes = _format_degrees(longitude)
    return f"{deg:02d}°{minutes:02d}' {sign}"


def to_xlsx(planets: list[PlanetPosition], houses: Houses, path: str | Path) -> None:
    """Placeholder for future XLSX export using openpyxl."""

    raise NotImplementedError("XLSX export is not implemented yet. Use print_text for now.")


def to_docx(planets: list[PlanetPosition], houses: Houses, path: str | Path) -> None:
    """Placeholder for future DOCX/ODT export."""

    raise NotImplementedError("DOCX/ODT export is not implemented yet. Use print_text for now.")


def _format_degrees(longitude: float) -> tuple[int, int]:
    """Return (degrees_in_sign, minutes) for a longitude."""

    deg_in_sign_float = longitude % 30.0
    deg_int = int(deg_in_sign_float)
    minutes = int(round((deg_in_sign_float - deg_int) * 60))
    if minutes == 60:
        deg_int = (deg_int + 1) % 30
        minutes = 0
    return deg_int, minutes
