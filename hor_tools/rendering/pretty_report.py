"""Polished complete natal-report renderers.

These functions change presentation only. They consume the already calculated
technical report and PlanetReport objects and do not perform astrology.
"""

from __future__ import annotations

from datetime import timedelta
from html import escape

from ..analysis.technical import NatalTechnicalReport
from ..models import ChartInput, Houses, PlanetReport
from .technical import _position, _short_condition, _unique_aspects


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend(
        "| " + " | ".join(str(cell).replace("|", "\\|").replace("\n", "<br>") for cell in row) + " |"
        for row in rows
    )
    return "\n".join(lines)


def _relation_rows(reports: list[PlanetReport]) -> list[list[str]]:
    rows: list[list[str]] = []
    for report in reports:
        for item in report.receptions_given:
            rows.append([
                "Reception",
                f"{item.host} → {item.guest}",
                ", ".join(item.dignities),
                item.aspect_kind or "—",
            ])
        for item in report.generosities_given:
            rows.append([
                "Generosity",
                f"{item.host} → {item.guest}",
                ", ".join(item.dignities),
                "no aspect",
            ])
        for item in report.repulsions_given:
            rows.append([
                "Repulsion / odbojnost",
                f"{item.host} → {item.guest}",
                ", ".join(item.debilities),
                item.aspect_kind or "no major aspect",
            ])
    return rows


def _lot_md(lot) -> str:
    contacts = "; ".join(
        f"{hit.planet} {hit.kind} ({hit.orb:.2f}°)" for hit in lot.aspects
    ) or "none"
    sees = "yes" if lot.ruler_sees_lot else "no"
    return "\n".join([
        f"#### {lot.name} — {_position(lot.longitude)} · H{lot.house}",
        "",
        f"- **Ruler:** {lot.ruler} in H{lot.ruler_house or '—'} · sees the Lot: **{sees}**",
        f"- **Planetary contacts:** {contacts}",
        f"- **Formula:** `{lot.formula}`",
    ])


def build_pretty_markdown(
    chart: ChartInput,
    reports: list[PlanetReport],
    houses: Houses,
    technical: NatalTechnicalReport,
    legacy_markdown: str,
) -> str:
    """Return a complete but editor-friendly Markdown report."""
    local_dt = chart.datetime_utc + timedelta(hours=chart.tz_offset_hours)
    sex = "male" if chart.male is True else "female" if chart.male is False else "unknown"
    fortune = next(lot for lot in technical.lots.hermetic if lot.name == "Fortune")
    spirit = next(lot for lot in technical.lots.hermetic if lot.name == "Spirit")
    totals = technical.temperament.totals
    behaviour = technical.behaviour.primary or "unresolved"
    almuten = ", ".join(technical.almuten.almuten) or "—"

    parts = [
        f"# Natal Technical Report — {chart.name}",
        "",
        "> **Traditional natal worksheet.** The report calculates formal factors and technical conditions; interpretive synthesis remains with the astrologer where the method requires judgment.",
        "",
        "## At a glance",
        "",
        _md_table(
            ["Factor", "Result", "Factor", "Result"],
            [
                ["Sect", "Day" if technical.solar.is_day else "Night", "Ascendant", _position(houses.asc)],
                ["Planetary day / hour", f"{technical.day_ruler} / {technical.hour_ruler}", "MC", _position(houses.mc) if houses.mc is not None else "—"],
                ["Fortune", f"{_position(fortune.longitude)} · H{fortune.house}", "Spirit", f"{_position(spirit.longitude)} · H{spirit.house}"],
                ["Temperament", f"K {totals['K']} · S {totals['S']} · M {totals['M']} · F {totals['F']}", "Highest", ", ".join(technical.temperament.dominant)],
                ["Almuten Figuris", f"{almuten} ({technical.almuten.almuten_score})", "Ruler of behaviour", behaviour],
                ["Prenatal syzygy", _position(technical.syzygy_longitude), "Native sex", sex],
            ],
        ),
        "",
        "---",
        "",
        "## 1. Chart frame",
        "",
        _md_table(
            ["Item", "Value"],
            [
                ["Local time", local_dt.strftime("%Y-%m-%d %H:%M:%S")],
                ["UTC", chart.datetime_utc.strftime("%Y-%m-%d %H:%M:%S")],
                ["Location", f"{chart.location_name or '—'} · {chart.latitude:.6f}, {chart.longitude:.6f}"],
                ["Altitude", f"{chart.altitude_m:.0f} m" if chart.altitude_m is not None else "—"],
                ["Sect", "Day" if technical.solar.is_day else "Night"],
                ["Sun true altitude", f"{technical.solar.sun_true_altitude:+.4f}°"],
                ["Apparent sunrise / sunset", f"{technical.solar.sunrise_local:%H:%M:%S} / {technical.solar.sunset_local:%H:%M:%S}"],
                ["Planetary day / hour ruler", f"{technical.day_ruler} / {technical.hour_ruler}"],
            ],
        ),
        "",
        "_Sect is determined from the Sun's true geometric altitude. Apparent sunrise and sunset are used for planetary-hour division._",
        "",
        "## 2. Planets",
        "",
        _md_table(
            ["Planet", "Position", "H", "Condition", "Phase"],
            [
                [
                    report.planet.name,
                    _position(report.planet.longitude),
                    str(report.planet.house),
                    _short_condition(report),
                    report.planet.synodic_phase.label if report.planet.synodic_phase else "—",
                ]
                for report in reports
            ],
        ),
        "",
        "### Major degree contacts",
        "",
        _md_table(
            ["Pair", "Aspect", "Orb", "State"],
            [
                [f"{a} – {b}", kind, f"{orb:.2f}°", state]
                for a, b, kind, orb, state in _unique_aspects(reports)
            ],
        ),
        "",
        "## 3. Houses",
        "",
        _md_table(
            ["H", "Sign", "Ruler", "Ruler located", "Occupants"],
            [
                [str(row.house), row.sign, row.ruler, f"H{row.ruler_house}", ", ".join(row.occupants) or "—"]
                for row in technical.houses
            ],
        ),
        "",
        "## 4. Reception, generosity and repulsion",
        "",
        _md_table(["Type", "Direction", "Basis", "Contact"], _relation_rows(reports)),
        "",
        "## 5. Lots",
        "",
        "The Lot itself has no orb. Listed contacts are rays cast by planets using the planet's own orb.",
        "",
        "### Seven Hermetic Lots",
        "",
        *sum(([_lot_md(lot), ""] for lot in technical.lots.hermetic), []),
        "### Topical Lots",
        "",
        *sum(([_lot_md(lot), ""] for lot in technical.lots.topical), []),
    ]

    if technical.lots.unsupported:
        parts.extend([
            "### Deliberately not calculated",
            "",
            *[f"- **{item.name}:** {item.reason}" for item in technical.lots.unsupported],
            "",
        ])

    parts.extend([
        "## 6. Temperament",
        "",
        f"> **Totals:** K **{totals['K']}** · S **{totals['S']}** · M **{totals['M']}** · F **{totals['F']}**  ",
        f"> **Highest:** {', '.join(technical.temperament.dominant)}",
        "",
        _md_table(
            ["Factor", "Evidence", "K", "S", "M", "F"],
            [
                [
                    row.factor,
                    "; ".join(row.evidence) or "—",
                    str(row.scores["K"]),
                    str(row.scores["S"]),
                    str(row.scores["M"]),
                    str(row.scores["F"]),
                ]
                for row in technical.temperament.rows
            ],
        ),
        "",
        "## 7. Primary motivation — factors",
        "",
        *sum(([
            f"### {factor.source}",
            f"- **Element:** {factor.element}",
            f"- **Formal motivation:** {factor.motivation}",
            f"- **Evidence:** {factor.detail}",
            f"- **Condition:** {', '.join(factor.condition) or '—'}",
            "",
        ] for factor in technical.primary_motivation.factors), []),
        "**Elemental count:** " + " · ".join(
            f"{key} {value}" for key, value in technical.primary_motivation.elemental_counts.items()
        ),
        "",
        f"_{technical.primary_motivation.note}_",
        "",
        "## 8. Ruler of behaviour",
        "",
        _md_table(
            ["Field", "Result"],
            [
                ["Primary", technical.behaviour.primary or "unresolved"],
                ["Candidates", ", ".join(technical.behaviour.candidates) or "—"],
                ["Secondary / Asc ruler", technical.behaviour.secondary or "—"],
                ["Rule applied", technical.behaviour.rule],
            ],
        ),
        "",
        *[f"- {item}" for item in technical.behaviour.evidence],
        "",
        "## 9. Ruler of geniture — evidence only",
        "",
        _md_table(
            ["Planet", "H", "Mundane", "Essential", "Accidental"],
            [
                [
                    item.planet,
                    str(item.house),
                    item.mundane_class,
                    ", ".join(item.essential_condition),
                    ", ".join(item.accidental_condition),
                ]
                for item in technical.geniture.candidates
            ],
        ),
        "",
        f"_{technical.geniture.note}_",
        "",
        "## 10. Quality of mind — technical factors",
        "",
        "### Mercury — rational mind",
        "",
        *[f"- {item}" for item in technical.mind.mercury],
        "",
        "### Moon — sensory / irrational mind",
        "",
        *[f"- {item}" for item in technical.mind.moon],
        "",
        "### Almutens",
        "",
        _md_table(
            ["Point", "Almuten", "Score"],
            [
                ["Mercury degree", ", ".join(technical.mind.mercury_almuten.winners) or "—", str(technical.mind.mercury_almuten.score)],
                ["Moon degree", ", ".join(technical.mind.moon_almuten.winners) or "—", str(technical.mind.moon_almuten.score)],
                ["Composite Almuten of Mind", ", ".join(technical.mind.composite_almuten.winners) or "—", str(technical.mind.composite_almuten.score)],
            ],
        ),
        "",
        "### Secondary contacts",
        "",
        *([f"- {item}" for item in technical.mind.secondary_contacts] or ["- none"]),
        "",
        "### Mercury–Moon relationship",
        "",
        *[f"- {item}" for item in technical.mind.mercury_moon_relation],
        "",
        f"_{technical.mind.note}_",
        "",
        "## 11. Duads / dodekatemoria",
        "",
        "A **5° orb** is used only when a planetary duad is tested against the Ascendant for temperament/behaviour testimony.",
        "",
        _md_table(
            ["Body / point", "Natal position", "Duad"],
            [[item.name, _position(item.source_longitude), _position(item.duad.longitude)] for item in technical.duads],
        ),
        "",
        "## 12. Almuten Figuris",
        "",
        f"> **Almuten Figuris:** **{almuten}** · score **{technical.almuten.almuten_score}**",
        "",
        _md_table(
            ["Planet", "Essential", "Accidental", "Grand total"],
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
        "<details>",
        "<summary><strong>13. Full legacy calculation tables</strong> — expand for every detailed planetary and relationship table</summary>",
        "",
        legacy_markdown,
        "",
        "</details>",
        "",
    ])
    return "\n".join(parts)


def _html_table(headers: list[str], rows: list[list[str]], cls: str = "") -> str:
    head = "".join(f"<th>{escape(str(x))}</th>" for x in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f'<div class="table-wrap"><table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def _html_list(items: list[str]) -> str:
    if not items:
        return "<p class=muted>None.</p>"
    return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"


def _lot_html(lot) -> str:
    contacts = "; ".join(f"{h.planet} {h.kind} ({h.orb:.2f}°)" for h in lot.aspects) or "none"
    sees = "Yes" if lot.ruler_sees_lot else "No"
    return f"""
    <article class="lot-card">
      <div class="lot-title"><strong>{escape(lot.name)}</strong><span>{escape(_position(lot.longitude))} · H{lot.house}</span></div>
      <div class="lot-grid">
        <div><small>Ruler</small><b>{escape(lot.ruler)} · H{lot.ruler_house or '—'}</b></div>
        <div><small>Ruler sees Lot</small><b>{sees}</b></div>
      </div>
      <p><small>Planetary contacts</small><br>{escape(contacts)}</p>
      <p class="formula"><small>Formula</small><br><code>{escape(lot.formula)}</code></p>
    </article>"""


def build_pretty_html(
    chart: ChartInput,
    reports: list[PlanetReport],
    houses: Houses,
    technical: NatalTechnicalReport,
    legacy_markdown: str,
) -> str:
    """Return a self-contained responsive HTML technical report."""
    local_dt = chart.datetime_utc + timedelta(hours=chart.tz_offset_hours)
    sex = "male" if chart.male is True else "female" if chart.male is False else "unknown"
    fortune = next(lot for lot in technical.lots.hermetic if lot.name == "Fortune")
    spirit = next(lot for lot in technical.lots.hermetic if lot.name == "Spirit")
    totals = technical.temperament.totals
    almuten = ", ".join(technical.almuten.almuten) or "—"
    behaviour = technical.behaviour.primary or "unresolved"

    planet_rows = [[
        r.planet.name,
        _position(r.planet.longitude),
        str(r.planet.house),
        _short_condition(r),
        r.planet.synodic_phase.label if r.planet.synodic_phase else "—",
    ] for r in reports]
    aspect_rows = [[f"{a} – {b}", kind, f"{orb:.2f}°", state] for a,b,kind,orb,state in _unique_aspects(reports)]
    house_rows = [[str(x.house), x.sign, x.ruler, f"H{x.ruler_house}", ", ".join(x.occupants) or "—"] for x in technical.houses]
    temp_rows = [[x.factor, "; ".join(x.evidence) or "—", str(x.scores['K']), str(x.scores['S']), str(x.scores['M']), str(x.scores['F'])] for x in technical.temperament.rows]
    geniture_rows = [[x.planet, str(x.house), x.mundane_class, ", ".join(x.essential_condition), ", ".join(x.accidental_condition)] for x in technical.geniture.candidates]
    duad_rows = [[x.name, _position(x.source_longitude), _position(x.duad.longitude)] for x in technical.duads]
    almuten_rows = [[p, str(technical.almuten.essential_totals.get(p,0)), str(technical.almuten.accidental.accidental_totals.get(p,0)), str(technical.almuten.grand_scores.get(p,0))] for p in technical.almuten.grand_scores]

    motivation_html = "".join(
        f'<article class="factor-card"><h3>{escape(f.source)}</h3><div class="tag">{escape(f.element)}</div><p><b>{escape(f.motivation)}</b></p><p>{escape(f.detail)}</p><p class="muted">{escape(", ".join(f.condition) or "—")}</p></article>'
        for f in technical.primary_motivation.factors
    )
    lots_hermetic = "".join(_lot_html(x) for x in technical.lots.hermetic)
    lots_topical = "".join(_lot_html(x) for x in technical.lots.topical)
    unsupported = _html_list([f"{x.name}: {x.reason}" for x in technical.lots.unsupported])

    css = """
:root{--bg:#f5f1e8;--paper:#fffdf8;--ink:#292722;--muted:#6d675c;--line:#ded5c7;--accent:#795f3d;--soft:#eee6d8;--good:#e6eee4;--bad:#f3e2df}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 Georgia,'Times New Roman',serif}
a{color:var(--accent)}.layout{display:grid;grid-template-columns:230px minmax(0,1fr);max-width:1500px;margin:auto;min-height:100vh}.side{position:sticky;top:0;height:100vh;padding:28px 18px;border-right:1px solid var(--line);background:#eee8dd}.side strong{display:block;font-size:19px;margin-bottom:18px}.side a{display:block;text-decoration:none;padding:5px 0;color:#544b40;font-family:system-ui,sans-serif;font-size:13px}.report{background:var(--paper);padding:56px 64px;min-width:0}h1{font-size:38px;margin:0 0 8px}h2{font-size:27px;margin:56px 0 18px;padding-bottom:8px;border-bottom:1px solid var(--line)}h3{font-size:18px}p{max-width:900px}.subtitle,.muted,small{color:var(--muted)}.hero{margin-bottom:34px}.eyebrow{text-transform:uppercase;letter-spacing:.12em;font:600 12px system-ui,sans-serif;color:var(--accent)}.snapshot{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:12px}.card,.factor-card,.lot-card{border:1px solid var(--line);background:#fff;padding:16px;border-radius:8px}.card small,.lot-card small{display:block;font:600 11px system-ui,sans-serif;text-transform:uppercase;letter-spacing:.06em}.card b{font-size:18px}.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:7px;background:#fff}table{border-collapse:collapse;width:100%;font-family:system-ui,sans-serif;font-size:13px}th{text-align:left;background:var(--soft);font-size:12px;letter-spacing:.02em}th,td{padding:9px 11px;border-bottom:1px solid #eee7dc;vertical-align:top}.lot-list{display:grid;grid-template-columns:repeat(2,minmax(280px,1fr));gap:12px}.lot-title{display:flex;justify-content:space-between;gap:12px;border-bottom:1px solid var(--line);padding-bottom:8px}.lot-title span{color:var(--muted)}.lot-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:12px 0}.formula{margin-bottom:0}.factor-grid{display:grid;grid-template-columns:repeat(2,minmax(260px,1fr));gap:12px}.factor-card h3{margin:0 0 6px}.tag{display:inline-block;background:var(--soft);padding:2px 8px;border-radius:999px;font:600 11px system-ui,sans-serif;text-transform:uppercase}.scorebar{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}.score{padding:8px 12px;border-radius:6px;background:var(--soft);font-family:system-ui,sans-serif}.score b{font-size:20px}details{border:1px solid var(--line);border-radius:8px;padding:12px 14px;background:#fff;margin:18px 0}summary{cursor:pointer;font-weight:bold}.legacy{white-space:pre-wrap;font:12px/1.45 ui-monospace,SFMono-Regular,Consolas,monospace;overflow:auto;background:#faf8f3;padding:14px;border-radius:6px}code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.9em}ul{padding-left:22px}
@media(max-width:1000px){.layout{display:block}.side{position:relative;height:auto;border-right:0;border-bottom:1px solid var(--line)}.side a{display:inline-block;margin-right:12px}.report{padding:36px 24px}.snapshot{grid-template-columns:repeat(2,1fr)}.lot-list,.factor-grid{grid-template-columns:1fr}}
@media(max-width:600px){.snapshot{grid-template-columns:1fr}.report{padding:28px 15px}h1{font-size:30px}.lot-title{display:block}}
@media print{body{background:#fff}.layout{display:block}.side{display:none}.report{padding:0}.card,.lot-card,.factor-card,.table-wrap,details{break-inside:avoid}h2{break-after:avoid}}
"""
    nav = [
        ("frame","Chart frame"),("planets","Planets"),("houses","Houses"),("relations","Relationships"),
        ("lots","Lots"),("temperament","Temperament"),("motivation","Primary motivation"),("behaviour","Behaviour"),
        ("geniture","Geniture"),("mind","Quality of mind"),("duads","Duads"),("almuten","Almuten Figuris"),("details","Full detailed tables")
    ]
    nav_html = "".join(f'<a href="#{i}">{escape(t)}</a>' for i,t in nav)

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Natal Technical Report — {escape(chart.name)}</title><style>{css}</style></head>
<body><div class="layout"><nav class="side"><strong>{escape(chart.name)}<br>Natal Report</strong>{nav_html}</nav><main class="report">
<header class="hero"><div class="eyebrow">Traditional astrology · technical worksheet</div><h1>Natal Technical Report</h1><p class="subtitle">{escape(chart.name)} · {local_dt:%Y-%m-%d %H:%M} local · {escape(chart.location_name or 'location')} </p></header>
<section class="snapshot">
<div class="card"><small>Sect</small><b>{'Day' if technical.solar.is_day else 'Night'}</b><div>{technical.day_ruler} day · {technical.hour_ruler} hour</div></div>
<div class="card"><small>Ascendant</small><b>{escape(_position(houses.asc))}</b><div>MC {escape(_position(houses.mc)) if houses.mc is not None else '—'}</div></div>
<div class="card"><small>Fortune / Spirit</small><b>{escape(_position(fortune.longitude))}</b><div>Spirit {escape(_position(spirit.longitude))}</div></div>
<div class="card"><small>Temperament</small><b>K {totals['K']} · S {totals['S']} · M {totals['M']} · F {totals['F']}</b><div>{escape(', '.join(technical.temperament.dominant))}</div></div>
<div class="card"><small>Almuten Figuris</small><b>{escape(almuten)}</b><div>score {technical.almuten.almuten_score}</div></div>
<div class="card"><small>Ruler of behaviour</small><b>{escape(behaviour)}</b><div>secondary {escape(technical.behaviour.secondary or '—')}</div></div>
<div class="card"><small>Prenatal syzygy</small><b>{escape(_position(technical.syzygy_longitude))}</b></div>
<div class="card"><small>Native sex</small><b>{escape(sex.title())}</b></div>
</section>

<section id="frame"><h2>1. Chart frame</h2>{_html_table(['Item','Value'],[
['Local time',local_dt.strftime('%Y-%m-%d %H:%M:%S')],['UTC',chart.datetime_utc.strftime('%Y-%m-%d %H:%M:%S')],
['Location',f"{chart.location_name or '—'} · {chart.latitude:.6f}, {chart.longitude:.6f}"],['Altitude',f"{chart.altitude_m:.0f} m" if chart.altitude_m is not None else '—'],
['Sect','Day' if technical.solar.is_day else 'Night'],['Sun true altitude',f"{technical.solar.sun_true_altitude:+.4f}°"],
['Apparent sunrise / sunset',f"{technical.solar.sunrise_local:%H:%M:%S} / {technical.solar.sunset_local:%H:%M:%S}"],['Planetary day / hour',f"{technical.day_ruler} / {technical.hour_ruler}"]])}<p class="muted">Sect uses the Sun's true geometric altitude; apparent sunrise/sunset is used for planetary-hour division.</p></section>

<section id="planets"><h2>2. Planets</h2>{_html_table(['Planet','Position','H','Condition','Phase'],planet_rows)}<h3>Major degree contacts</h3>{_html_table(['Pair','Aspect','Orb','State'],aspect_rows)}</section>
<section id="houses"><h2>3. Houses</h2>{_html_table(['H','Sign','Ruler','Ruler located','Occupants'],house_rows)}</section>
<section id="relations"><h2>4. Reception, generosity and repulsion</h2>{_html_table(['Type','Direction','Basis','Contact'],_relation_rows(reports))}</section>
<section id="lots"><h2>5. Lots</h2><p class="muted">Lots have no orb of their own. Contacts shown here are rays cast by planets using the planet's orb.</p><h3>Seven Hermetic Lots</h3><div class="lot-list">{lots_hermetic}</div><h3>Topical Lots</h3><div class="lot-list">{lots_topical}</div><details><summary>Deliberately not calculated</summary>{unsupported}</details></section>
<section id="temperament"><h2>6. Temperament</h2><div class="scorebar"><div class="score">K <b>{totals['K']}</b></div><div class="score">S <b>{totals['S']}</b></div><div class="score">M <b>{totals['M']}</b></div><div class="score">F <b>{totals['F']}</b></div></div><p><b>Highest:</b> {escape(', '.join(technical.temperament.dominant))}</p>{_html_table(['Factor','Evidence','K','S','M','F'],temp_rows)}</section>
<section id="motivation"><h2>7. Primary motivation — factors</h2><div class="factor-grid">{motivation_html}</div><p><b>Elemental count:</b> {escape(' · '.join(f'{k} {v}' for k,v in technical.primary_motivation.elemental_counts.items()))}</p><p class="muted">{escape(technical.primary_motivation.note)}</p></section>
<section id="behaviour"><h2>8. Ruler of behaviour</h2>{_html_table(['Field','Result'],[['Primary',technical.behaviour.primary or 'unresolved'],['Candidates',', '.join(technical.behaviour.candidates) or '—'],['Secondary / Asc ruler',technical.behaviour.secondary or '—'],['Rule applied',technical.behaviour.rule]])}{_html_list(technical.behaviour.evidence)}</section>
<section id="geniture"><h2>9. Ruler of geniture — evidence only</h2>{_html_table(['Planet','H','Mundane','Essential','Accidental'],geniture_rows)}<p class="muted">{escape(technical.geniture.note)}</p></section>
<section id="mind"><h2>10. Quality of mind — technical factors</h2><div class="factor-grid"><article class="factor-card"><h3>Mercury — rational mind</h3>{_html_list(technical.mind.mercury)}</article><article class="factor-card"><h3>Moon — sensory / irrational mind</h3>{_html_list(technical.mind.moon)}</article></div><h3>Almutens</h3>{_html_table(['Point','Almuten','Score'],[['Mercury degree',', '.join(technical.mind.mercury_almuten.winners) or '—',str(technical.mind.mercury_almuten.score)],['Moon degree',', '.join(technical.mind.moon_almuten.winners) or '—',str(technical.mind.moon_almuten.score)],['Composite Almuten of Mind',', '.join(technical.mind.composite_almuten.winners) or '—',str(technical.mind.composite_almuten.score)]])}<h3>Secondary contacts</h3>{_html_list(technical.mind.secondary_contacts)}<h3>Mercury–Moon relationship</h3>{_html_list(technical.mind.mercury_moon_relation)}<p class="muted">{escape(technical.mind.note)}</p></section>
<section id="duads"><h2>11. Duads / dodekatemoria</h2><p class="muted">A fixed 5° orb is used only when a planetary duad is tested against the Ascendant for temperament/behaviour testimony.</p>{_html_table(['Body / point','Natal position','Duad'],duad_rows)}</section>
<section id="almuten"><h2>12. Almuten Figuris</h2><p><b>{escape(almuten)}</b> · score <b>{technical.almuten.almuten_score}</b></p>{_html_table(['Planet','Essential','Accidental','Grand total'],almuten_rows)}</section>
<section id="details"><h2>13. Full detailed calculation tables</h2><details><summary>Expand legacy planetary / relationship output</summary><pre class="legacy">{escape(legacy_markdown)}</pre></details></section>
</main></div></body></html>"""
