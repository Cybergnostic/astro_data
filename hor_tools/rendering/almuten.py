"""Text and Rich rendering for Almuten Figuris results."""

from __future__ import annotations

from ..almuten import (
    ALMUTEN_PLANETS,
    DAY_RULER_BONUS,
    HOUR_RULER_BONUS,
    build_almuten_figuris,
)
from ..analysis.dignity import SIGNS
from ..models import ChartInput, Houses, PlanetPosition


def _format_degrees(longitude: float) -> tuple[int, int]:
    deg_in_sign_float = longitude % 30.0
    deg_int = int(deg_in_sign_float)
    minutes = int(round((deg_in_sign_float - deg_int) * 60))
    if minutes == 60:
        deg_int = (deg_int + 1) % 30
        minutes = 0
    return deg_int, minutes


def _format_degree_for_table(longitude: float) -> str:
    sign = SIGNS[int(longitude // 30) % 12]
    deg_in_sign, minutes = _format_degrees(longitude)
    return f"{deg_in_sign:02d}°{minutes:02d}' {sign:<8}"


def _format_contrib_cell(contribs: list[int]) -> str:
    return "+".join(str(value) for value in contribs) if contribs else ""


def _format_row_header(title: str) -> str:
    return f"{title:<8}"


def print_almuten_tables(
    chart: ChartInput,
    planets: list[PlanetPosition],
    houses: Houses,
    console=None,
) -> None:
    """Compute and print Almuten Figuris essential, accidental and total scores."""
    try:
        from rich import box
        from rich.console import Console as RichConsole
        from rich.table import Table
    except ModuleNotFoundError:
        RichConsole = None  # type: ignore[assignment]
        Table = None  # type: ignore[assignment]

    result = build_almuten_figuris(chart, planets, houses)
    rows = result.rows
    total_shares = result.total_shares
    essential_totals = result.essential_totals
    accidental = result.accidental
    grand_scores = result.grand_scores
    almuten = result.almuten
    almuten_score = result.almuten_score

    if RichConsole is None or Table is None:
        print("ESSENTIAL")
        header = f"{'point':<8}{'degree':<18}"
        for planet in ALMUTEN_PLANETS:
            header += f"{planet.lower():<10}"
        header += "degree wins"
        print(header)

        for row in rows:
            line = (
                f"{_format_row_header(row.name)}"
                f"{_format_degree_for_table(row.longitude):<18}"
            )
            for planet in ALMUTEN_PLANETS:
                cell = _format_contrib_cell(row.contributions.get(planet, []))
                line += f"{cell:<10}"
            if row.winners:
                line += ", ".join(
                    f"{winner} ({row.totals.get(winner, 0)})" for winner in row.winners
                )
            print(line)

        share_line = f"{'TOTAL SHARES':<26}"
        for planet in ALMUTEN_PLANETS:
            share_line += f"{total_shares.get(planet, 0):<10}"
        print(share_line)

        score_line = f"{'TOTAL SCORES':<26}"
        for planet in ALMUTEN_PLANETS:
            score_line += f"{essential_totals.get(planet, 0):<10}"
        print(score_line)

        print("\nACCIDENTAL")
        header_acc = f"{'':<18}"
        for planet in ALMUTEN_PLANETS:
            header_acc += f"{planet.lower():<10}"
        print(header_acc)

        house_line = f"{'house scores':<18}"
        for planet in ALMUTEN_PLANETS:
            house_line += f"{accidental.house_scores.get(planet, 0):<10}"
        print(house_line)

        print(f"day ruler: {accidental.day_ruler}, +{DAY_RULER_BONUS}")
        print(f"hour ruler: {accidental.hour_ruler}, +{HOUR_RULER_BONUS}")

        phase_line = f"{'phase score':<18}"
        for planet in ALMUTEN_PLANETS:
            phase_line += f"{accidental.phase_scores.get(planet, 0):<10}"
        print(phase_line)

        print("\nTOTALS")
        header_tot = f"{'total':<18}"
        for planet in ALMUTEN_PLANETS:
            header_tot += f"{planet.lower():<10}"
        print(header_tot)

        essential_line = f"{'essential scores':<18}"
        for planet in ALMUTEN_PLANETS:
            essential_line += f"{essential_totals.get(planet, 0):<10}"
        print(essential_line)

        accidental_line = f"{'accidental scores':<18}"
        for planet in ALMUTEN_PLANETS:
            accidental_line += f"{accidental.accidental_totals.get(planet, 0):<10}"
        print(accidental_line)

        grand_line = f"{'grand scores':<18}"
        for planet in ALMUTEN_PLANETS:
            grand_line += f"{grand_scores.get(planet, 0):<10}"
        print(grand_line)

        if almuten:
            print(f"\nALMUTEN FIGURIS: {', '.join(almuten)} ({almuten_score})")
        return

    rich_console = console if console is not None else RichConsole()

    def highlight_row(
        values: dict[str, int], emphasize: set[str] | None = None
    ) -> list[str]:
        if not values:
            return ["0"] * len(ALMUTEN_PLANETS)
        max_value = max(values.values())
        styled: list[str] = []
        for planet in ALMUTEN_PLANETS:
            value = values.get(planet, 0)
            if emphasize and planet in emphasize:
                styled.append(f"[black on cyan]{value}[/]")
            elif max_value > 0 and value == max_value:
                styled.append(f"[bold green]{value}[/]")
            else:
                styled.append(str(value))
        return styled

    table_width = 110
    rich_console.print(
        "[bold underline magenta]Almuten Figuris – Essential and Accidental Scores[/]"
    )
    rich_console.print(
        "[dim]Row highs in green; grand winner highlighted in the combined totals below.[/]"
    )

    essential_table = Table(
        title="Essential dignity shares (sign, exaltation, triplicity, term, face)",
        box=box.MINIMAL_DOUBLE_HEAD,
        expand=False,
        width=table_width,
        padding=(0, 1),
    )
    essential_table.add_column("Point", style="cyan", no_wrap=True)
    essential_table.add_column("Degree", style="magenta", no_wrap=True)
    for planet in ALMUTEN_PLANETS:
        essential_table.add_column(planet, justify="center", no_wrap=True, style="white")
    essential_table.add_column("Winner", style="green", overflow="fold", max_width=20)

    for row in rows:
        winner = ", ".join(row.winners) if row.winners else ""
        essential_table.add_row(
            row.name,
            _format_degree_for_table(row.longitude),
            *(
                _format_contrib_cell(row.contributions.get(planet, []))
                for planet in ALMUTEN_PLANETS
            ),
            winner,
        )

    summary_table = Table(
        title="Essential dignity totals (shares + scores)",
        box=box.SIMPLE_HEAVY,
        expand=False,
        width=table_width,
        padding=(0, 1),
    )
    summary_table.add_column("Total Shares", no_wrap=True, style="cyan")
    for planet in ALMUTEN_PLANETS:
        summary_table.add_column(planet, justify="center", no_wrap=True, style="white")
    summary_table.add_row("Shares", *highlight_row(total_shares))
    summary_table.add_row("Scores", *highlight_row(essential_totals))

    accidental_table = Table(
        title="Accidental strength (House, phase, day/hour bonuses)",
        box=box.SIMPLE,
        expand=False,
        width=table_width,
        padding=(0, 1),
    )
    accidental_table.add_column("Component", no_wrap=True, style="cyan")
    for planet in ALMUTEN_PLANETS:
        accidental_table.add_column(planet, justify="center", no_wrap=True, style="white")
    accidental_table.add_row("House", *highlight_row(accidental.house_scores))
    accidental_table.add_row("Phase", *highlight_row(accidental.phase_scores))
    accidental_table.add_row("Day bonus", *highlight_row(accidental.day_bonus))
    accidental_table.add_row("Hour bonus", *highlight_row(accidental.hour_bonus))

    totals_table = Table(
        title="Combined Essential + Accidental",
        box=box.DOUBLE_EDGE,
        expand=False,
        width=table_width,
        padding=(0, 1),
    )
    totals_table.add_column("Type", no_wrap=True, style="cyan")
    for planet in ALMUTEN_PLANETS:
        totals_table.add_column(planet, justify="center", no_wrap=True, style="white")
    totals_table.add_row("Essential", *highlight_row(essential_totals))
    totals_table.add_row("Accidental", *highlight_row(accidental.accidental_totals))
    totals_table.add_row("Grand", *highlight_row(grand_scores, emphasize=set(almuten)))

    rich_console.print(essential_table)
    rich_console.print(summary_table)
    rich_console.print(accidental_table)
    rich_console.print(totals_table)

    if almuten:
        names = ", ".join(almuten)
        detail_bits = [
            f"{name} [dim](essential {essential_totals.get(name, 0)} + accidental "
            f"{accidental.accidental_totals.get(name, 0)})[/]"
            for name in almuten
        ]
        rich_console.print(
            f"[bold magenta]Almuten Figuris:[/] {names} ([green]{almuten_score}[/]) "
            "— highest combined score."
        )
        rich_console.print(f"[dim]{'; '.join(detail_bits)}[/]")
