"""Render the compact terminal snapshot and complete Markdown worksheet."""

from __future__ import annotations

from datetime import timedelta

from ..analysis.dignity import SIGNS
from ..analysis.technical import NatalTechnicalReport
from ..models import ChartInput, Houses, PlanetReport

PLANET_SYMBOLS = {
    "Sun": "☉",
    "Moon": "☽",
    "Mercury": "☿",
    "Venus": "♀",
    "Mars": "♂",
    "Jupiter": "♃",
    "Saturn": "♄",
}


def _position(longitude: float) -> str:
    longitude %= 360.0
    sign = SIGNS[int(longitude // 30.0)]
    within = longitude % 30.0
    degree = int(within)
    minutes_float = (within - degree) * 60.0
    minute = int(minutes_float)
    second = int(round((minutes_float - minute) * 60.0))
    if second >= 60:
        second = 0
        minute += 1
    if minute >= 60:
        minute = 0
        degree += 1
    return f"{degree:02d}°{minute:02d}'{second:02d}\" {sign}"


def _short_condition(report: PlanetReport) -> str:
    items: list[str] = []
    if report.is_domicile:
        items.append("dom")
    if report.is_exalted:
        items.append("exalt")
    if report.is_detriment:
        items.append("detr")
    if report.is_fall:
        items.append("fall")
    if not any((report.is_domicile, report.is_exalted, report.is_detriment, report.is_fall)):
        items.append("—")
    if report.in_sect:
        items.append("sect")
    if report.hayz:
        items.append("hayz")
    if report.planet.retrograde:
        items.append("Rx")
    elif report.planet.station:
        items.append(f"station:{report.planet.station}")
    if report.is_true_cazimi:
        items.append("true-cazimi")
    elif report.is_cazimi:
        items.append("cazimi")
    return ", ".join(items)


def _unique_aspects(reports: list[PlanetReport]) -> list[tuple[str, str, str, float, str]]:
    seen: set[tuple[str, str]] = set()
    result: list[tuple[str, str, str, float, str]] = []
    for report in reports:
        for aspect in report.aspects:
            key = tuple(sorted((report.planet.name, aspect.other)))
            if key in seen:
                continue
            seen.add(key)
            result.append(
                (
                    report.planet.name,
                    aspect.other,
                    aspect.kind,
                    aspect.orb,
                    "app" if aspect.applying else "sep",
                )
            )
    return sorted(result, key=lambda item: item[3])


def print_terminal_summary(
    chart: ChartInput,
    reports: list[PlanetReport],
    houses: Houses,
    technical: NatalTechnicalReport,
) -> None:
    """Print the intentionally compact working view."""
    try:
        from rich import box
        from rich.console import Console
        from rich.table import Table
    except ModuleNotFoundError:  # pragma: no cover
        _print_plain_summary(chart, reports, houses, technical)
        return

    console = Console()
    local_dt = chart.datetime_utc + timedelta(hours=chart.tz_offset_hours)
    console.print(f"[bold cyan]{chart.name}[/] — {local_dt:%Y-%m-%d %H:%M:%S} local")

    frame = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    frame.add_column(style="cyan")
    frame.add_column()
    frame.add_row("Sect", "DAY" if technical.solar.is_day else "NIGHT")
    frame.add_row("Sunrise", technical.solar.sunrise_local.strftime("%H:%M:%S"))
    frame.add_row("Sunset", technical.solar.sunset_local.strftime("%H:%M:%S"))
    frame.add_row("Sun true altitude", f"{technical.solar.sun_true_altitude:+.2f}°")
    frame.add_row("Planetary day / hour", f"{technical.day_ruler} / {technical.hour_ruler}")
    frame.add_row("Ascendant", _position(houses.asc))
    if houses.mc is not None:
        frame.add_row("MC", _position(houses.mc))
    frame.add_row("Prenatal syzygy", _position(technical.syzygy_longitude))
    fortune = next(lot for lot in technical.lots.hermetic if lot.name == "Fortune")
    spirit = next(lot for lot in technical.lots.hermetic if lot.name == "Spirit")
    frame.add_row("Fortune", f"{_position(fortune.longitude)}  H{fortune.house}")
    frame.add_row("Spirit", f"{_position(spirit.longitude)}  H{spirit.house}")
    console.print(frame)

    totals = technical.temperament.totals
    console.print(
        f"[bold]Temperament:[/] K {totals['K']} | S {totals['S']} | "
        f"M {totals['M']} | F {totals['F']}  → {' / '.join(technical.temperament.dominant)}"
    )
    console.print(
        f"[bold]Almuten Figuris:[/] {', '.join(technical.almuten.almuten) or '—'} "
        f"({technical.almuten.almuten_score})"
    )
    behaviour = technical.behaviour.primary or "unresolved"
    if technical.behaviour.primary is None and technical.behaviour.candidates:
        behaviour += f" ({', '.join(technical.behaviour.candidates)})"
    secondary = f"; secondary {technical.behaviour.secondary}" if technical.behaviour.secondary else ""
    console.print(f"[bold]Ruler of behaviour:[/] {behaviour}{secondary}")
    console.print()

    table = Table(title="Planetary Snapshot", box=box.SIMPLE, padding=(0, 1))
    table.add_column("Planet", style="cyan")
    table.add_column("Position", style="magenta")
    table.add_column("H", justify="right")
    table.add_column("Condition")
    table.add_column("Phase")
    for report in reports:
        phase = report.planet.synodic_phase.label if report.planet.synodic_phase else "—"
        table.add_row(
            f"{PLANET_SYMBOLS.get(report.planet.name, '')} {report.planet.name}",
            _position(report.planet.longitude),
            str(report.planet.house),
            _short_condition(report),
            phase,
        )
    console.print(table)

    aspects = _unique_aspects(reports)
    if aspects:
        aspect_table = Table(title="Major Degree Contacts", box=box.SIMPLE, padding=(0, 1))
        aspect_table.add_column("Pair")
        aspect_table.add_column("Aspect")
        aspect_table.add_column("Orb", justify="right")
        aspect_table.add_column("State")
        for first, second, kind, orb, state in aspects:
            aspect_table.add_row(f"{first} – {second}", kind, f"{orb:.2f}°", state)
        console.print(aspect_table)

    relation_rows: list[tuple[str, str]] = []
    for report in reports:
        for reception in report.receptions_given:
            relation_rows.append(
                ("Reception", f"{reception.host} receives {reception.guest} ({', '.join(reception.dignities)})")
            )
        for generosity in report.generosities_given:
            relation_rows.append(
                ("Generosity", f"{generosity.host} → {generosity.guest} ({', '.join(generosity.dignities)})")
            )
        for repulsion in report.repulsions_given:
            relation_rows.append(
                ("Repulsion", f"{repulsion.host} → {repulsion.guest} ({', '.join(repulsion.debilities)})")
            )
    if relation_rows:
        rel_table = Table(title="Reception / Generosity / Repulsion", box=box.SIMPLE, padding=(0, 1))
        rel_table.add_column("Type")
        rel_table.add_column("Relation")
        for kind, detail in relation_rows:
            rel_table.add_row(kind, detail)
        console.print(rel_table)


def _print_plain_summary(
    chart: ChartInput,
    reports: list[PlanetReport],
    houses: Houses,
    technical: NatalTechnicalReport,
) -> None:
    print(chart.name)
    print("Sect:", "day" if technical.solar.is_day else "night")
    print("Sunrise / Sunset:", technical.solar.sunrise_local.time(), technical.solar.sunset_local.time())
    print("Day / Hour ruler:", technical.day_ruler, "/", technical.hour_ruler)
    print("Asc:", _position(houses.asc))
    print("Temperament:", technical.temperament.totals, technical.temperament.dominant)
    print("Almuten Figuris:", technical.almuten.almuten, technical.almuten.almuten_score)
    behaviour = technical.behaviour.primary or "unresolved"
    if technical.behaviour.primary is None and technical.behaviour.candidates:
        behaviour += f" ({', '.join(technical.behaviour.candidates)})"
    print("Ruler of behaviour:", behaviour)
    for report in reports:
        print(report.planet.name, _position(report.planet.longitude), "H", report.planet.house, _short_condition(report))


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend(
        "| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |"
        for row in rows
    )
    return "\n".join(lines)


def build_technical_markdown(
    chart: ChartInput,
    reports: list[PlanetReport],
    houses: Houses,
    technical: NatalTechnicalReport,
    legacy_markdown: str,
) -> str:
    """Return the complete technical worksheet plus the existing detailed tables."""
    local_dt = chart.datetime_utc + timedelta(hours=chart.tz_offset_hours)
    native_sex = "male" if chart.male is True else "female" if chart.male is False else "unknown"
    parts: list[str] = [
        f"# Natal Technical Report — {chart.name}",
        "",
        "## 1. Chart Frame",
        "",
        _md_table(
            ["Item", "Value"],
            [
                ["Local time", local_dt.strftime("%Y-%m-%d %H:%M:%S")],
                ["UTC", chart.datetime_utc.strftime("%Y-%m-%d %H:%M:%S")],
                ["Location", f"{chart.latitude:.6f}, {chart.longitude:.6f}"],
                ["Native sex (Morinus)", native_sex],
                ["Sect", "Day" if technical.solar.is_day else "Night"],
                ["Apparent sunrise", technical.solar.sunrise_local.strftime("%H:%M:%S")],
                ["Apparent sunset", technical.solar.sunset_local.strftime("%H:%M:%S")],
                ["Sun true altitude", f"{technical.solar.sun_true_altitude:+.4f}°"],
                ["Planetary day ruler", technical.day_ruler],
                ["Planetary hour ruler", technical.hour_ruler],
                ["Ascendant", _position(houses.asc)],
                ["MC", _position(houses.mc) if houses.mc is not None else "—"],
                ["Prenatal syzygy", _position(technical.syzygy_longitude)],
            ],
        ),
        "",
        "Sect uses the Sun's true geometric altitude; apparent sunrise/sunset is retained for planetary-hour divisions.",
        "",
        "## 2. House Structure",
        "",
        _md_table(
            ["House", "Sign", "Ruler", "Ruler in", "Occupants"],
            [
                [str(row.house), row.sign, row.ruler, f"H{row.ruler_house}", ", ".join(row.occupants) or "—"]
                for row in technical.houses
            ],
        ),
        "",
        "## 3. Duads / Dodekatemoria",
        "",
        "Temperament and behaviour supplements use a fixed **5° orb** when a planetary duad is tested against the Ascendant.",
        "",
        _md_table(
            ["Body / Point", "Source position", "Duad"],
            [[item.name, _position(item.source_longitude), _position(item.duad.longitude)] for item in technical.duads],
        ),
        "",
        "## 4. Reception, Generosity and Repulsion",
        "",
    ]

    relation_rows: list[list[str]] = []
    for report in reports:
        for reception in report.receptions_given:
            relation_rows.append([
                "Reception", reception.host, reception.guest,
                ", ".join(reception.dignities), reception.aspect_kind or "—",
            ])
        for generosity in report.generosities_given:
            relation_rows.append([
                "Generosity", generosity.host, generosity.guest,
                ", ".join(generosity.dignities), "no aspect",
            ])
        for repulsion in report.repulsions_given:
            relation_rows.append([
                "Repulsion (odbojnost)", repulsion.host, repulsion.guest,
                ", ".join(repulsion.debilities), repulsion.aspect_kind or "no major aspect",
            ])
    parts.append(
        _md_table(["Type", "From / host", "To / guest", "Basis", "Contact"], relation_rows)
        if relation_rows else "No reception, generosity or repulsion relationships."
    )

    parts.extend(["", "## 5. Lots", "", "### Seven Hermetic Lots", ""])
    parts.append(
        _md_table(
            ["Lot", "Position", "H", "Ruler", "Ruler in", "Ruler sees Lot", "Planetary contacts", "Formula"],
            [
                [
                    lot.name,
                    _position(lot.longitude),
                    str(lot.house),
                    lot.ruler,
                    f"H{lot.ruler_house}" if lot.ruler_house else "—",
                    "yes" if lot.ruler_sees_lot else "no",
                    "; ".join(f"{hit.planet} {hit.kind} {hit.orb:.2f}°" for hit in lot.aspects) or "—",
                    lot.formula,
                ]
                for lot in technical.lots.hermetic
            ],
        )
    )
    parts.extend(["", "### Topical Lots", ""])
    parts.append(
        _md_table(
            ["Lot", "Position", "H", "Ruler", "Ruler in", "Ruler sees Lot", "Planetary contacts", "Formula"],
            [
                [
                    lot.name,
                    _position(lot.longitude),
                    str(lot.house),
                    lot.ruler,
                    f"H{lot.ruler_house}" if lot.ruler_house else "—",
                    "yes" if lot.ruler_sees_lot else "no",
                    "; ".join(f"{hit.planet} {hit.kind} {hit.orb:.2f}°" for hit in lot.aspects) or "—",
                    lot.formula,
                ]
                for lot in technical.lots.topical
            ],
        )
    )
    if technical.lots.unsupported:
        parts.extend(["", "### Deliberately not calculated", ""])
        parts.extend(f"- **{item.name}:** {item.reason}" for item in technical.lots.unsupported)

    parts.extend(["", "## 6. Temperament", ""])
    parts.append(
        _md_table(
            ["Factor", "Evidence", "K", "S", "M", "F", "Note"],
            [
                [
                    row.factor,
                    "; ".join(row.evidence) or "—",
                    str(row.scores["K"]), str(row.scores["S"]),
                    str(row.scores["M"]), str(row.scores["F"]),
                    row.note or "",
                ]
                for row in technical.temperament.rows
            ],
        )
    )
    totals = technical.temperament.totals
    parts.extend([
        "",
        f"**Totals:** K {totals['K']} · S {totals['S']} · M {totals['M']} · F {totals['F']}",
        f"**Highest:** {', '.join(technical.temperament.dominant)}",
        "",
        "## 7. Primary Motivation — Factors",
        "",
        _md_table(
            ["Source", "Element", "Formal motivation", "Detail", "Condition"],
            [
                [factor.source, factor.element, factor.motivation, factor.detail, ", ".join(factor.condition) or "—"]
                for factor in technical.primary_motivation.factors
            ],
        ),
        "",
        "Elemental factor count: " + ", ".join(
            f"{key}={value}" for key, value in technical.primary_motivation.elemental_counts.items()
        ),
        "",
        f"_{technical.primary_motivation.note}_",
        "",
        "## 8. Ruler of Behaviour",
        "",
        f"**Primary:** {technical.behaviour.primary or 'unresolved'}",
        f"**Candidates:** {', '.join(technical.behaviour.candidates) or '—'}",
        f"**Secondary:** {technical.behaviour.secondary or '—'}",
        f"**Rule applied:** {technical.behaviour.rule}",
        *[f"- {item}" for item in technical.behaviour.evidence],
        "",
        "## 9. Ruler of Geniture — Evidence Only",
        "",
        _md_table(
            ["Planet", "House", "Mundane class", "Essential", "Accidental"],
            [
                [item.planet, str(item.house), item.mundane_class, ", ".join(item.essential_condition), ", ".join(item.accidental_condition)]
                for item in technical.geniture.candidates
            ],
        ),
        "",
        f"_{technical.geniture.note}_",
        "",
        "## 10. Quality of Mind — Technical Factors",
        "",
        "### Mercury (rational mind)",
        *[f"- {item}" for item in technical.mind.mercury],
        "",
        "### Moon (sensory / irrational mind)",
        *[f"- {item}" for item in technical.mind.moon],
        "",
        f"**Almuten of Mercury degree:** {', '.join(technical.mind.mercury_almuten.winners) or '—'} ({technical.mind.mercury_almuten.score})",
        f"**Almuten of Moon degree:** {', '.join(technical.mind.moon_almuten.winners) or '—'} ({technical.mind.moon_almuten.score})",
        f"**Composite Almuten of Mind:** {', '.join(technical.mind.composite_almuten.winners) or '—'} ({technical.mind.composite_almuten.score})",
        "",
        "### Secondary contacts",
        *([f"- {item}" for item in technical.mind.secondary_contacts] or ["- none"]),
        "",
        "### Mercury–Moon relationship",
        *[f"- {item}" for item in technical.mind.mercury_moon_relation],
        "",
        f"_{technical.mind.note}_",
        "",
        "## 11. Almuten Figuris — Summary",
        "",
        f"**Almuten:** {', '.join(technical.almuten.almuten) or '—'} ({technical.almuten.almuten_score})",
        "",
        _md_table(
            ["Planet", "Essential", "Accidental", "Grand"],
            [
                [
                    planet,
                    str(technical.almuten.essential_totals.get(planet, 0)),
                    str(technical.almuten.accidental.accidental_totals.get(planet, 0)),
                    str(technical.almuten.grand_scores.get(planet, 0)),
                ]
                for planet in technical.almuten.grand_scores
            ],
        ),
        "",
        "## 12. Detailed Planetary / Relationship Tables",
        "",
        legacy_markdown,
        "",
    ])
    return "\n".join(parts)
