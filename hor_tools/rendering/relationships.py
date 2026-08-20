"""Rich tables for chart-level traditional relationship doctrines."""

from __future__ import annotations

from ..models import ChartRelationships, InfluenceSource, PlanetReport


def render_relationship_tables(
    console,
    reports: list[PlanetReport],
    relationships: ChartRelationships,
    use_narrow_icons: bool = False,
) -> None:
    """Render bonification, domination, translation, collection and reception tables."""
    from rich import box
    from rich.table import Table

    def aspect_label(kind: str) -> str:
        clean = kind.replace("_", " ")
        if "decimation" in clean:
            parts = clean.split()
            if len(parts) == 2:
                return f"{parts[0]} (decimation)"
        return clean

    def domination_phrase(reason: str) -> str:
        relation = reason.replace("domination_", "").replace("counter_domination_", "")
        return aspect_label(relation)

    ben_icon = "+" if use_narrow_icons else "✅"
    mal_icon = "x" if use_narrow_icons else "❌"
    dom_icon = "#" if use_narrow_icons else "🛡"
    feral_icon = "o" if use_narrow_icons else "🕳"

    def format_ray_entries(sources: list[InfluenceSource], icon: str) -> list[str]:
        grouped: dict[str, set[str]] = {}
        for source in sources:
            grouped.setdefault(source.planet, set()).add(source.reason)

        rays: list[str] = []
        for planet, reasons in grouped.items():
            aspect_reason = next((r for r in reasons if r.startswith("ray_")), None)
            conjunction = "conjunction" in reasons
            applying = "applying" in reasons
            special = next(
                (r for r in reasons if r.endswith("_trine") or r.endswith("_opposition")),
                None,
            )
            if aspect_reason:
                aspect = aspect_reason.replace("ray_", "").replace("_", " ")
                phrase = f"{aspect} ray from {planet}"
            elif conjunction:
                phrase = f"conjoined with {planet} (<=3°)"
            elif special:
                short = (
                    special.replace("benefic_", "")
                    .replace("malefic_", "")
                    .replace("_", " ")
                )
                phrase = f"{short} from {planet}"
            else:
                phrase = f"from {planet}"
            if applying:
                phrase += " (applying)"
            rays.append(f"{icon} {phrase}")
        return rays or ["—"]

    def format_domination_entries(
        sources: list[InfluenceSource], enclosure_flags: list[str], icon: str
    ) -> list[str]:
        entries: list[str] = []
        for source in sources:
            if source.reason.startswith("domination_"):
                entries.append(
                    f"{icon} dominated by {source.planet} ({domination_phrase(source.reason)})"
                )
            if source.reason.startswith("counter_domination_"):
                entries.append(
                    f"{icon} counter-ray from {source.planet} "
                    f"({domination_phrase(source.reason)})"
                )
            if source.reason == "dispositor":
                entries.append(f"{icon} {source.planet} as sign ruler (dispositor)")
        entries.extend(enclosure_flags)
        return entries or ["—"]

    legend = (
        f"[green]{ben_icon} benefic / help[/]    "
        f"[red]{mal_icon} malefic / harm[/]    "
        f"[yellow]{dom_icon} domination / enclosure[/]    "
        f"[magenta]{feral_icon} feral or special[/]"
    )
    console.print(legend)
    console.print()

    condition_table = Table(
        title="Bonification / Maltreatment",
        box=box.MINIMAL_DOUBLE_HEAD,
        expand=False,
        width=120,
        padding=(0, 1),
        caption="Who is helping or harming each planet (rays vs domination/enclosure).",
    )
    condition_table.add_column("Planet", style="cyan", no_wrap=True)
    condition_table.add_column("Benefic rays", style="green", overflow="fold", max_width=24)
    condition_table.add_column("Malefic rays", style="red", overflow="fold", max_width=24)
    condition_table.add_column(
        "Benefic dom/enclosure", style="yellow", overflow="fold", max_width=28
    )
    condition_table.add_column(
        "Malefic dom/enclosure", style="yellow", overflow="fold", max_width=28
    )
    condition_table.add_column("Feral", style="magenta", no_wrap=True)

    for report in reports:
        ben_rays = (
            format_ray_entries(report.bonification_sources, ben_icon)
            if report.is_bonified
            else ["—"]
        )
        mal_rays = (
            format_ray_entries(report.maltreatment_sources, mal_icon)
            if report.is_maltreated
            else ["—"]
        )

        enclosure_ben: list[str] = []
        enclosure_mal: list[str] = []
        if report.benefic_enclosure_by_sign:
            enclosure_ben.append(f"{dom_icon} enclosed by benefics (sign)")
        if report.benefic_enclosure_by_ray:
            enclosure_ben.append(f"{dom_icon} enclosed by benefic rays")
        if report.malefic_enclosure_by_sign:
            enclosure_mal.append(f"{dom_icon} enclosed by malefics (sign)")
        if report.malefic_enclosure_by_ray:
            enclosure_mal.append(f"{dom_icon} enclosed by malefic rays")

        ben_dom = format_domination_entries(
            [
                source
                for source in report.bonification_sources
                if "domination" in source.reason or source.reason == "dispositor"
            ],
            enclosure_ben,
            dom_icon,
        )
        mal_dom = format_domination_entries(
            [
                source
                for source in report.maltreatment_sources
                if "domination" in source.reason or source.reason == "dispositor"
            ],
            enclosure_mal,
            dom_icon,
        )

        feral = f"[magenta]{feral_icon} YES[/]" if report.is_feral else "—"
        condition_table.add_row(
            report.planet.name,
            "\n".join(ben_rays),
            "\n".join(mal_rays),
            "\n".join(ben_dom),
            "\n".join(mal_dom),
            feral,
        )

    console.print(condition_table)
    console.print()

    domination_table = Table(
        title="Domination / Counter-rays",
        box=box.MINIMAL,
        expand=False,
        width=110,
        padding=(0, 1),
        caption="Who has the upper hand by sign distance; counter-ray shows the comeback.",
    )
    domination_table.add_column("Dominator", style="cyan", no_wrap=True)
    domination_table.add_column("Dominated", style="magenta", no_wrap=True)
    domination_table.add_column("Aspect of domination", style="yellow", no_wrap=True)
    domination_table.add_column("Counter-ray", style="green", no_wrap=True)

    if relationships.dominations:
        for domination in relationships.dominations:
            counter = "[dim]—[/]"
            if domination.has_counter_ray:
                orb = f" ({domination.orb:.2f}°)" if domination.orb is not None else ""
                counter = f"[bold green]✅ counter-ray[/]{orb}"
            domination_table.add_row(
                domination.dominator,
                domination.dominated,
                aspect_label(domination.relationship),
                counter,
            )
    else:
        domination_table.add_row("—", "—", "—", "—")
    console.print(domination_table)
    console.print()

    translation_table = Table(
        title="Translation of Light",
        box=box.SIMPLE,
        expand=False,
        width=110,
        padding=(0, 1),
        caption="A faster planet carries a relationship from one planet to another.",
    )
    translation_table.add_column("Translator", style="cyan", no_wrap=True)
    translation_table.add_column(
        "Connecting (From → To)", style="magenta", overflow="fold", max_width=36
    )
    translation_table.add_column("Action", style="yellow", overflow="fold", max_width=54)

    def translator_style(name: str) -> str:
        if name in {"Venus", "Jupiter"}:
            return f"[green]{name}[/]"
        if name in {"Mars", "Saturn"}:
            return f"[red]{name}[/]"
        return f"[cyan]{name}[/]"

    if relationships.translations:
        for translation in relationships.translations:
            chain = f"{translation.from_planet} → {translation.to_planet}"
            action = (
                f"moves from {aspect_label(translation.aspect_from.kind)} with "
                f"{translation.from_planet} to {aspect_label(translation.aspect_to.kind)} with "
                f"{translation.to_planet} (translates light)"
            )
            if not translation.naturally_fastest:
                action += " [dim](fast now, not by nature)[/]"
            translation_table.add_row(
                translator_style(translation.translator), chain, action
            )
    else:
        translation_table.add_row("—", "—", "—")
    console.print(translation_table)
    console.print()

    collection_table = Table(
        title="Collection of Light",
        box=box.SIMPLE,
        expand=False,
        width=110,
        padding=(0, 1),
        caption="A slower hub receives two applying aspects and gathers their promise.",
    )
    collection_table.add_column("Collector", style="cyan", no_wrap=True)
    collection_table.add_column(
        "Planets being collected", style="magenta", overflow="fold", max_width=36
    )
    collection_table.add_column("Action", style="yellow", overflow="fold", max_width=54)

    if relationships.collections:
        for collection in relationships.collections:
            from_pair = f"{collection.from_planets[0]} & {collection.from_planets[1]}"
            action = (
                f"receives {aspect_label(collection.aspect_from_first.kind)} from "
                f"{collection.from_planets[0]} and "
                f"{aspect_label(collection.aspect_from_second.kind)} from "
                f"{collection.from_planets[1]}; {collection.collector} slower → collects their light"
            )
            notes: list[str] = []
            if not collection.collector_naturally_slower:
                notes.append("collector only currently slower")
            if collection.naturally_fastest:
                notes.append(f"naturally fastest feeder: {collection.naturally_fastest}")
            if notes:
                action += f" ({'; '.join(notes)})"
            collection_table.add_row(
                f"[bold cyan]{collection.collector}[/]", from_pair, action
            )
    else:
        collection_table.add_row("—", "—", "—")
    console.print(collection_table)
    console.print()

    reception_table = Table(
        title="Receptions / Generosities",
        box=box.MINIMAL,
        expand=False,
        width=110,
        padding=(0, 1),
    )
    reception_table.add_column("Host", style="cyan", no_wrap=True)
    reception_table.add_column("Guest", style="magenta", no_wrap=True)
    reception_table.add_column("Type", style="yellow", no_wrap=True)
    reception_table.add_column("Dignities", style="green", overflow="fold", max_width=30)
    reception_table.add_column("Aspect", style="white", no_wrap=True)

    rows_added = False
    for report in reports:
        for reception in report.receptions_given:
            reception_table.add_row(
                reception.host,
                reception.guest,
                "reception",
                "/".join(reception.dignities),
                reception.aspect_kind or "—",
            )
            rows_added = True
        for generosity in report.generosities_given:
            reception_table.add_row(
                generosity.host,
                generosity.guest,
                "generosity",
                "/".join(generosity.dignities),
                "—",
            )
            rows_added = True
    if not rows_added:
        reception_table.add_row("—", "—", "—", "—", "—")
    console.print(reception_table)
    console.print()
