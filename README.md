hor-tools
=========

`hor-tools` reads classic Morinus `.hor` files, normalizes the chart data, calculates traditional astrology with Swiss Ephemeris, and renders a technical report in the terminal, HTML, or Markdown.

The project uses the traditional planets Sun through Saturn, Tropical zodiac, and Whole Sign houses for house placement. Ascendant and MC are astronomical angles calculated by Swiss Ephemeris.

Preview
-------
![hor-reader terminal dashboard](docs/img/report_example.png)

Requirements
------------
- Python 3.11+
- `uv`
- Swiss Ephemeris data files

Setup
-----
```bash
cd astro_data
uv sync --all-groups
```

Swiss Ephemeris
---------------
Ephemeris files are not bundled. Point the program at your Swiss Ephemeris directory either with `SWISSEPH_EPHE` or `--ephe`.

```bash
export SWISSEPH_EPHE=~/.local/share/swisseph

# or per command
uv run hor-reader --ephe ~/.local/share/swisseph chart.hor
```

The configured path must exist. Fixed-star reports additionally depend on the Swiss fixed-star catalogue available to pyswisseph (normally `sefstars.txt` in the ephemeris directory).

Main command
------------
```bash
uv run hor-reader --help
uv run hor-reader chart.hor
uv run hor-reader --ephe /path/to/ephe chart.hor
uv run hor-reader chart.hor --html report.html --md report.md
```

Simple relative export names are written under `outputs/`, so the last command creates:

```text
outputs/report.html
outputs/report.md
```

`hor-reader` uses normal `argparse` validation. Unknown options, missing option values, multiple input files, malformed `.hor` files, and invalid ephemeris paths fail explicitly instead of being silently guessed. Use `--debug` when you want a Python traceback.

Morinus `.hor` support
----------------------
The parser targets the classic Morinus protocol-0 natal/radix header used by the project. It validates the serialized fields rather than scanning arbitrary integers.

Currently supported time forms:
- Gregorian calendar
- zone/civil time with east/west UTC offset and Morinus DST flag
- Greenwich time
- local mean time

Currently rejected explicitly rather than approximated:
- BC charts
- Julian-calendar `.hor` dates
- local apparent time

The parser preserves the chart name, place name, longitude, latitude, altitude, local UTC offset, and normalized UTC datetime. Invalid or incomplete coordinate data raises an error; it never falls back to `0°N, 0°E`.

What the report calculates
--------------------------
- Sun through Saturn positions and speeds
- Whole Sign houses, Ascendant, and MC
- essential dignities: domicile, exaltation, Dorothean triplicity, Egyptian terms, Chaldean faces
- detriment and fall
- chart sect, planetary sect, Hayz, Halb, oriental/occidental condition
- direct/retrograde motion, station state, and speed relative to mean motion
- solar/synodic phases, ordinary cazimi, and true longitude+latitude cazimi
- magnitude-sensitive course fixed-star conjunctions
- major aspects with the project/teacher planetary orbs
- applying/separating geometry, dexter/sinister, mutual application/separation, counter-rays
- antiscia and contra-antiscia
- planetary joys, latitude testimony, Via Combusta, lunar void-of-course
- domicile sight / aversion
- domination/decimation and aktinobolia
- bonification/maltreatment and benefic/malefic enclosure
- receptions and generosities
- translation and collection of light
- feral planets
- Almuten Figuris using the teacher-configured Morinus scoring, including all three triplicity rulers, day/hour bonuses, house scores, and Morinus superior-planet phase bands

Installed helper commands
-------------------------
The scanners are package commands, so after installation they do not depend on being launched from the repository root.

### Ingresses and exact aspects

```bash
uv run hor-scan-events \
  --start "2028-01-01T00:00:00Z" \
  --end "2028-02-01T00:00:00Z" \
  --lat 40.7 --lon -74.0 \
  --step-min 60 --tol-min 0.1 \
  --aspect 0=conj \
  --aspect 60=sextile \
  --aspect 90=square \
  --aspect 120=trine \
  --aspect 180=opp
```

The event scanner uses a lightweight longitude-only ephemeris path internally; it does not recalculate houses, stations, or synodic state during every refinement step. `--step-min` and `--tol-min` must be positive.

### Ascendant-window scanner

```bash
uv run hor-scan-asc \
  --primer path/to/template.hor \
  --start-date 2028-04-20 \
  --end-date 2028-05-05 \
  --window-start 12:00 \
  --window-end 18:00 \
  --step-min 10 \
  --tol-min 0.2 \
  --tz Europe/Belgrade
```

- The primer supplies the chart location and other metadata.
- Prefer an IANA timezone with `--tz` when the date range can cross a DST transition.
- Without `--tz`, the fixed civil offset stored in the `.hor` file is used and a warning is printed.
- Overnight daily windows are not currently supported; `window-end` must be later than `window-start`.
- Output defaults to `outputs/asc_scan_<start>_<end>.md`.
- Add `--verbose` to include Almuten tables in every generated report.

The old repository-root commands `uv run scan_events.py ...` and `uv run asc_window_scan.py ...` remain as compatibility wrappers.

Project layout
--------------
```text
hor_tools/
    cli.py                 main hor-reader command
    hor_parser.py          validated Morinus parser
    astro_engine.py        Swiss Ephemeris / raw astronomy
    models.py              normalized chart/report dataclasses
    almuten.py             Almuten calculations
    almuten_types.py       typed Almuten result objects
    synodic.py             synodic/solar phase logic
    analysis/              astrological analysis modules
    commands/              installed scanner commands
    output.py              report rendering/export

tests/
    fixtures/              representative input fixtures

.github/workflows/ci.yml  tests + build + clean-wheel smoke test
```

Development
-----------
Run the full suite with:

```bash
uv sync --all-groups
uv run pytest -q
uv run ruff check hor_tools tests scan_events.py asc_window_scan.py
```

Build the package with:

```bash
uv build
```

CI builds a real wheel, installs that wheel into a clean virtual environment, imports the `analysis` and `commands` subpackages, and smoke-tests all three console commands. This guards against packaging problems that an editable checkout can hide.

Architecture notes
------------------
`context.md` contains the maintainer-oriented architecture overview and domain boundaries. Calculation rules should live in calculation/analysis modules; CLI and renderer refactors should not silently change astrological doctrine.
