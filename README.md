hor-tools
=========

Read Morinus `.hor` files, normalize chart data, and compute placements with Swiss Ephemeris (pyswisseph). Uses Whole sign houses by default and is built to be extended with Lots and export formats later.

Requirements
------------
- Python 3.11+
- uv (https://github.com/astral-sh/uv) installed and on PATH
- Swiss Ephemeris data files (see below)

Setup
-----
```bash
# From repo root (astro_data)
uv sync
```

Ephemeris data
--------------
Swiss Ephemeris data files are required (planet/moon `.se1` files and `sefstars.txt` for fixed stars). Point the code at your ephemeris directory via environment variable `SWISSEPH_EPHE` (otherwise it defaults to `/home/cyber/swisseph_ephe`):
```bash
export SWISSEPH_EPHE=/path/to/ephemeris
```
Place the directory anywhere (e.g., `~/.local/share/swisseph` on Linux) and set the variable before running.

Usage
-----
```bash
# From repo root (astro_data)
uv run hor-reader Andjela_cybergnostic.hor

# Point at any Morinus .hor file
uv run hor-reader path/to/file.hor

# Use a specific ephemeris directory (overrides SWISSEPH_EPHE)
uv run hor-reader --ephe ~/projects/MorinusWin/SWEP/Ephem Andjela_cybergnostic.hor
```

What you get
------------
- Parsed chart input (UTC datetime, decimal lat/lon, tz offset stored).
- Planet positions (Sun through Saturn) via Swiss Ephemeris, mapped to Whole sign houses.
- Derived Whole sign house cusps plus Ascendant/MC.
- Traditional analysis bundle per planet: dignities, sect/hayz/halb, motion class, synodic phase, fixed stars, and aspect flags (applying/separating, dexter/sinister, mutual application/separation, counter-rays).
- Relationship layers: domination/decimation (with aktinobolia), bonification/maltreatment sources, benefic/malefic enclosures, receptions/generosities, translations/collections of light (with natural-speed notes), feral planet marker.
- Rich console tables with dark HTML/markdown export; Almuten tables included.

Project layout
--------------
- Repo root (now `astro_data/`):
  - `pyproject.toml`, `uv.lock`
  - `hor_tools/` (package)
  - `tests/`
  - `context.md` (architecture overview)
  - Personal `.hor` files (git-ignored) can sit alongside.
- Entry point: `hor_tools/cli.py` (`hor-reader`).
- Core modules: `models.py`, `hor_parser.py`, `astro_engine.py`, `analysis/*`, `output.py`.

Extending
---------
- Configure ephemeris path in `astro_engine.py` (`EPHE_PATH` constant).
- Add Lots, aspects, dignities, or additional bodies in `astro_engine.py`.
- Relationship logic lives in `analysis/relationships.py`; aspect helpers in `analysis/aspects.py`.
- Implement exports in `output.py` (XLSX via `openpyxl`, DOCX/ODT via `python-docx` or `odfpy`).

Publish & install on another machine
------------------------------------
1) Publish to GitHub (once):
```bash
git init
git add .
git commit -m "Initial import of hor-tools"
gh repo create yourname/hor-tools --source=. --public --push  # or create on GitHub and git remote add origin ...
git push -u origin main
```

2) Install and run on another Linux/Mac machine (with uv installed):
```bash
git clone https://github.com/yourname/hor-tools.git
cd hor-tools
uv sync
export SWISSEPH_EPHE=/path/to/ephemeris  # set to your Swiss Ephemeris folder
uv run hor-reader path/to/file.hor --html report.html --md report.md
```
