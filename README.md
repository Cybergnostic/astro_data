# hor-tools

[![CI](https://github.com/Cybergnostic/astro_data/actions/workflows/ci.yml/badge.svg)](https://github.com/Cybergnostic/astro_data/actions/workflows/ci.yml)

`hor-tools` turns classic Morinus `.hor` files into a compact terminal snapshot and complete Traditional Astrology reports in Markdown and HTML.

It uses Sun through Saturn, the Tropical zodiac, Whole Sign houses, Swiss Ephemeris, and the project/course traditional rules. It is a **technical worksheet for the astrologer**, not an automatic natal-reading engine.

![hor-tools HTML report](docs/img/report_example.png)

*Fictional example chart; the screenshot shows the current HTML report layout.*

## Quick start

Requirements: Python 3.11+, [`uv`](https://docs.astral.sh/uv/), and Swiss Ephemeris files.

```bash
uv sync --all-groups
export SWISSEPH_EPHE=~/.local/share/swisseph

uv run hor-reader chart.hor
```

The normal command prints the compact terminal view and automatically creates:

```text
outputs/chart_report.md
```

Generate HTML too:

```bash
uv run hor-reader chart.hor --html chart.html
```

Simple output names are written under `outputs/`.

Useful options:

```bash
uv run hor-reader chart.hor --md custom.md
uv run hor-reader chart.hor --html chart.html --no-md
uv run hor-reader chart.hor --verbose-terminal
uv run hor-reader --help
```

## What it covers

- planetary positions, dignities, debilities, sect, Hayz/Halb, motion and synodic state
- traditional major aspects, application/separation, antiscia and related relationship doctrines
- reception, generosity and repulsion (`odbojnost`)
- fixed stars and lunar/planetary conditions
- duads / dodekatemoria
- Hermetic and supported topical Lots
- planetary day and hour
- temperament
- Primary Motivation factors
- Ruler of Behaviour
- Quality-of-Mind factors and Almuten of Mind
- Almuten Figuris

Where the source requires qualitative judgment, the program presents the factors instead of manufacturing a final interpretation.

## Example reports

- [Markdown report](outputs/jovan.md)
- [HTML report](outputs/jovan.html)

## Other commands

```bash
uv run hor-scan-events --help
uv run hor-scan-asc --help
```

`hor-scan-events` scans ingresses and exact aspects. `hor-scan-asc` scans Ascendant-sign windows and supports IANA timezones for DST-aware ranges.

## Development

```bash
uv run ruff check hor_tools tests scan_events.py asc_window_scan.py
uv run pytest -q
uv build
```

CI runs lint, tests, package builds, clean-wheel imports, and CLI smoke tests.

## Documentation

See [`context.md`](context.md) for the architecture, calculation boundaries, parser details, source-specific rules, and maintainer notes.

Electional material lives in [`docs/electional_astrology_rules.md`](docs/electional_astrology_rules.md).
