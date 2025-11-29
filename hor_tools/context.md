Project purpose
---------------
Read Morinus `.hor` files, build a neutral internal chart representation, and calculate traditional Astrology data using Swiss Ephemeris (pyswisseph). The goal is to produce a rich, machine-usable, and visually styled terminal dashboard for each planet: sign, House, dignities, sect condition, motion, aspects, fixed stars, synodic phases, and Almuten scoring.

Current capabilities
--------------------
- Parse Morinus `.hor` natal files into a typed `ChartInput`:
  - Name
  - UTC datetime (with timezone + DST handled)
  - Decimal latitude/longitude
  - House system (Whole sign) and zodiac (Tropical)
- Compute:
  - Planetary positions (Sun - Saturn) with Swiss Ephemeris
  - Whole sign Houses from the Ascendant sign
  - Ascendant and MC from Swiss Ephemeris
  - Planetary hours/day rulers aligned with Morinus local civil date (sunrise→sunrise), timezone/DST fixed
- Build a full traditional planet report (`PlanetReport`) for each planet:
  - Essential dignity:
    - Sign ruler / domicile
    - Exaltation
    - Dorothean triplicity
    - Egyptian terms
    - Chaldean decans (faces)
    - Debility flags: detriment, fall
  - Sect and condition:
    - Day/night chart
    - Planet sect (day/night, Mercury by oriental/occidental) with corrected oriental/occidental logic
    - In sect or out of sect
    - Hayz and Halb (hemisphere condition)
    - Oriental / occidental relative to the Sun
  - Motion:
    - Direct / retrograde
    - Daily speed in longitude
    - Speed compared to mean (ratio + class: slow / average / swift)
    - Ecliptic latitude
  - Synodic phases (superior, inferior, lunar) with elongation/orientation and stations
  - Phase scoring (Ezra-style) for superior planets using elongation bands
  - Fixed stars (1st/2nd magnitude list) within a user-defined orb (default 3°) using `sefstars.txt`
  - Aspects to other traditional planets:
    - Aspect type (conjunction, sextile, square, trine, opposition)
    - Orb using the larger of the two planetary orbs
    - Applying vs separating (using real speeds, including retrograde)
    - Dexter vs sinister
- Render a high-fidelity terminal dashboard using `rich`:
  - **Planetary State Table**:
    - Columns: Planet, Position, House, Dignity, Sect, Motion, Synodic
    - Multiline cells: Dignity (ruler/exalt/trip/term/face/debility), Sect (chart/planet, in-sect, hayz, halb, orientation), Motion (direction/speed/lat)
    - Color-coded highlights: retrograde/slow, domicile/exalt/debility, in-sect/hayz/halb, orientation
    - Spacer rows between planets for readability
  - **Aspects Table**:
    - Columns: Pair, Aspect, Orb (tight orbs highlighted), Status (applying/separating), Polarity (dexter/sinister)
    - Sorted by orb tightness
  - **Houses & Angles**:
    - Compact “Houses (Whole sign)” table (house + sign only)
    - Separate “Angles” table for Asc/MC
    - Sign symbols suppressed in Rich/HTML to keep mono widths aligned
  - **Almuten Tables**:
    - Colored, with maxima highlighted per row and winners in green
  - Export options:
    - `--html out.html` saves a dark-themed HTML that matches the console layout (monospace, fixed widths)
    - `--md out.md` saves a fenced code snapshot of the Rich/text output

Architecture
------------
- `hor_tools/models.py`
  - `ChartInput`: normalized birth data from Morinus `.hor`
  - `PlanetPosition`: raw planetary data (lon/lat, speed, House, retrograde, synodic info)
  - `Houses`: Whole sign cusps + Asc + MC
  - `AspectInfo`: one aspect from a planet to another planet
  - `PlanetReport`: full analysis bundle for a single planet
- `hor_tools/hor_parser.py`
  - Reads Morinus `.hor` files (ASCII), extracts:
    - Name
    - Timezone and DST (base + DST flag)
    - Date and time
    - Coordinates (lon/lat) from the final int block
  - Produces `ChartInput` in UTC
- `hor_tools/astro_engine.py`
  - Swiss Ephemeris wrapper with a shared `EPHE_PATH` (points to ephemeris directory)
  - `compute_planets(chart)`: planets Sun - Saturn + Whole sign Houses
    - Uses `FLG_SWIEPH | FLG_SPEED` to get speed and retrograde
    - Fills elongation_from_sun and synodic_phase per planet
  - `compute_houses(chart)`: Asc/MC + Whole sign cusps
  - `julian_day_from_chart(chart)`: helper to reuse JD in other modules
- `hor_tools/analysis/`
  - `dignity.py`: rulers, exaltations, triplicities, terms, faces; mean speeds
  - `sect.py`: chart sect, planet sect, hayz/halb, horizon tests
  - `aspects.py`: aspect detection, orbs, applying/separating, dexter/sinister
  - `stars.py`: fixed star lookup via Swiss Ephemeris
  - `__init__.py`: `build_reports` glue for all analysis
- `hor_tools/output.py`
  - Rich/text/markdown rendering of reports; synodic column included
  - Almuten tables rendered with Rich (fallback to text)
  - HTML export (`export_rich_html`) for dark-themed output
- `hor_tools/cli.py`
  - `hor-reader` console script entry point:
    - Usage: `hor-reader [--html out.html] [--md out.md] path/to/file.hor`
    - Steps:
      1. Parse `.hor` into `ChartInput`
      2. Compute planets and Houses
      3. Build `PlanetReport` list
      4. Render Rich tables to stdout (or text if Rich missing)
      5. Optional HTML/Markdown export

External requirements
---------------------
- Python 3.11+
- `pyswisseph` installed via uv/pyproject
- `rich` installed via uv/pyproject (for terminal output)
- Ephemeris data:
  - Directory with:
    - Planet and Moon `.se1` files (e.g. `sepl_*.se1`, `semo_*.se1`, `seas_*.se1`)
    - **`sefstars.txt`** for fixed stars
  - `EPHE_PATH` in `astro_engine.py` must point to that folder
- Morinus `.hor` files exported in the expected format

Future work
-----------
- Add calculation of lots (Fortune, Spirit, etc.) using day/night formulas.
- Add reception and collection/perfection detection based on aspects and dignities.
- Implement XLSX export (via `openpyxl`) for tabular technical data.
- Implement DOCX/ODT export (via `python-docx` / `odfpy`) for formatted written reports.
- Flags to control which sections are printed (e.g. hide aspects or fixed stars).
