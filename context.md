Project purpose
---------------
`hor-tools` is a Traditional Astrology calculation/reporting package built around Morinus `.hor` input and Swiss Ephemeris. The architectural goal is to keep four concerns separate:

1. input normalization;
2. astronomical calculation;
3. astrological doctrine/calculation;
4. presentation and command-line behavior.

Engineering refactors should not silently change astrological rules. Source-backed doctrine belongs in calculation modules and should be protected by regression tests.

Architecture
------------

### Input model — `hor_tools/hor_parser.py`, `hor_tools/models.py`

`load_hor()` parses the classic Morinus protocol-0 natal/radix header into `ChartInput`.

The parser validates the actual serialized Morinus fields rather than searching arbitrary integers. It currently supports Gregorian zone time, Greenwich time, and local mean time. BC dates, Julian-calendar dates, and local apparent time fail explicitly until implemented correctly.

`ChartInput` stores:
- chart name;
- normalized UTC datetime;
- civil UTC offset;
- latitude/longitude;
- house/zodiac identifiers;
- Morinus place name when present;
- altitude when present.

Invalid coordinates never fall back to `(0, 0)`.

### Astronomy — `hor_tools/astro_engine.py`

This layer owns Swiss Ephemeris interaction:
- Julian day conversion;
- Sun–Saturn positions and speeds;
- Ascendant and MC;
- Whole Sign house assignment;
- adjacent-day station detection;
- lightweight longitude-only calculation for event scanners.

`SWISSEPH_EPHE` or `--ephe` supplies the ephemeris directory. The path is validated before use; there is no machine-specific production default.

### Traditional analysis — `hor_tools/analysis/`

The analysis package is deliberately split by doctrine:
- `dignity.py`: domicile, exaltation, Dorothean triplicity, Egyptian terms, Chaldean faces, mean-speed comparison;
- `sect.py`: chart/planet sect, true-horizon Hayz/Halb;
- `aspects.py`: teacher/project planetary orbs, sign-configuration rules, applying/separating and dexter/sinister geometry;
- `ray_geometry.py`: exact major ray landing points used by relationship doctrines;
- `conditions.py`: planetary joy, latitude testimony, Via Combusta, lunar void-of-course;
- `antiscia.py`: antiscia/contra-antiscia;
- `aversion.py`: domicile sight and aversion;
- `stars.py`: course fixed-star catalogue with magnitude-sensitive orbs and latitude qualification;
- `relationships.py`: domination/decimation, aktinobolia, enclosure, bonification/maltreatment, reception/generosity, translation/collection, feral condition.

`analysis.build_reports()` is the orchestration layer that combines those calculations into typed `PlanetReport` instances.

### Synodic state — `hor_tools/synodic.py`

This module owns ordinary solar-contact conditions and the detailed superior/inferior/lunar synodic state machines. Ordinary cazimi and the stricter longitude+latitude true-cazimi testimony are kept distinct.

### Almuten Figuris — `hor_tools/almuten.py`, `hor_tools/almuten_types.py`

The Almuten calculation follows the teacher-configured Morinus setup rather than a generic software default:
- five life points: Sun, Moon, Ascendant, Fortune, prenatal syzygy;
- essential weights 5/4/3/2/1 for domicile/exaltation/triplicity/term/face;
- all three Dorothean triplicity rulers receive the triplicity share;
- Mercury exaltation in Virgo is used;
- accidental house scores match the teacher's Morinus options, including VIII=4 and IX=5;
- day ruler +7, hour ruler +6;
- superior-planet phase score uses the directional Morinus bands 18–30 / 30–40 / 40–80 / 80–100 / 100–120 with weights 1/2/3/2/1.

`AlmutenResult` and `AccidentalScores` provide typed result objects while retaining mapping compatibility for older renderer code.

### Presentation — `hor_tools/output.py`

The renderer currently owns text, Rich, HTML and Markdown presentation. It does not determine doctrine; it consumes typed calculation results.

`output.py` is the largest remaining module and is a natural target for gradual renderer-only splitting. Any split should preserve public output functions and be protected by existing rendering tests.

### Commands — `hor_tools/cli.py`, `hor_tools/commands/`

Installed console commands:
- `hor-reader` — read one `.hor` chart and render/export a report;
- `hor-scan-events` — ingress/exact-aspect scanner using the lightweight longitude API;
- `hor-scan-asc` — Ascendant-sign-window reports with optional IANA timezone support.

The old root `scan_events.py` and `asc_window_scan.py` files are compatibility wrappers only.

Testing and packaging
---------------------

`pyproject.toml` uses setuptools package discovery for `hor_tools*`, so subpackages such as `hor_tools.analysis` and `hor_tools.commands` are included in built distributions.

Runtime dependencies are separate from development dependencies. Pytest, Ruff and build tooling live in the dev dependency group.

Permanent CI (`.github/workflows/ci.yml`) performs:
- dependency installation;
- full pytest suite;
- package build;
- installation of the built wheel into a clean virtual environment;
- imports of package submodules;
- `--help` smoke tests for all installed commands.

This clean-wheel check is intentional: an editable source checkout can hide missing-package configuration.

Domain invariants worth protecting
----------------------------------
- Traditional planets only.
- Tropical zodiac.
- Whole Sign house placement.
- Teacher-supplied private planetary aspect orbs remain project overrides.
- Aspect existence follows the course's sign-configuration/out-of-sign rule, not unrestricted geometric closeness.
- True astronomical horizon is used where the doctrine requires above/below horizon.
- Almuten scoring follows the teacher's actual Morinus configuration.
- Calculation code should fail explicitly when an unsupported input would otherwise require guessing.

Future engineering work
-----------------------
- Continue splitting presentation-only responsibilities out of `output.py` without changing calculations.
- Add more representative anonymized Morinus fixtures if additional file variants are encountered.
- Add native support for Julian/BC/local-apparent Morinus inputs only after reproducing Morinus conversion semantics exactly.
- Optional structured export formats may be added behind separate extras.
