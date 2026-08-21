Project purpose
---------------
`hor-tools` is a Traditional Astrology calculation/reporting package built around Morinus `.hor` input and Swiss Ephemeris.

The architectural goal is to keep four concerns separate:

1. input normalization;
2. astronomical calculation;
3. astrological doctrine/calculation;
4. presentation and command-line behavior.

Engineering or renderer changes should not silently change astrological rules. Source-backed doctrine belongs in calculation modules and should be protected by regression tests.

Architecture
------------

### Input model — `hor_tools/hor_parser.py`, `hor_tools/models.py`

`load_hor()` parses the classic Morinus protocol-0 natal/radix header into `ChartInput`.

The parser validates the actual serialized Morinus fields instead of searching arbitrary integers. It currently supports Gregorian zone/civil time, Greenwich time, and local mean time. BC dates, Julian-calendar dates, and local apparent time fail explicitly until implemented correctly.

`ChartInput` preserves:
- chart name;
- native sex field when present;
- normalized UTC datetime;
- civil UTC offset;
- latitude/longitude;
- Morinus place name;
- altitude;
- house/zodiac identifiers.

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

The analysis package is split by doctrine rather than by presentation:

- `dignity.py`: domicile, exaltation, Dorothean triplicity, Egyptian terms, Chaldean faces, mean-speed comparison;
- `sect.py`: chart/planet sect, Hayz/Halb;
- `solar.py`: true sect state plus apparent sunrise/sunset and planetary day/hour framework;
- `aspects.py`: project/teacher planetary orbs, sign-configuration rules, applying/separating and dexter/sinister geometry;
- `ray_geometry.py`: exact major ray landing points used by relationship doctrines;
- `conditions.py`: planetary joy, latitude testimony, Via Combusta, lunar void-of-course;
- `antiscia.py`: antiscia/contra-antiscia;
- `aversion.py`: domicile sight and aversion;
- `stars.py`: course fixed-star catalogue with magnitude-sensitive rules;
- `relationships.py`: domination/decimation, aktinobolia, enclosure, bonification/maltreatment, reception, generosity, repulsion, translation/collection, feral condition;
- `duads.py`: duad/dodekatemorion calculations;
- `lots.py`: Hermetic and supported topical Lots, ruler sight, contacts, sex-specific marriage Lot, Father Lot conditional rule;
- `temperament.py`: formal temperament worksheet and totals;
- `natal_synthesis.py`: deterministic/evidence layers for Primary Motivation, Ruler of Behaviour, Geniture evidence, and Quality of Mind;
- `technical.py`: aggregate natal technical-report model.

`analysis.build_reports()` combines lower-level planetary calculations into typed `PlanetReport` instances. `build_natal_technical_report()` builds the higher-level natal worksheet from those results.

### Synodic state — `hor_tools/synodic.py`

This module owns ordinary solar-contact conditions and detailed superior/inferior/lunar synodic state machines.

Ordinary cazimi and the stricter longitude+latitude true-cazimi testimony are separate conditions. A planet in cazimi must not simultaneously be labelled combust/under beams by higher-level report code.

### Almuten Figuris — `hor_tools/almuten.py`, `hor_tools/almuten_types.py`

The Almuten calculation follows the teacher-configured Morinus setup rather than a generic software default:

- five life points: Sun, Moon, Ascendant, Fortune, prenatal syzygy;
- essential weights 5/4/3/2/1 for domicile/exaltation/triplicity/term/face;
- all three Dorothean triplicity rulers receive the triplicity share;
- Mercury exaltation in Virgo is used;
- accidental house scores match the teacher's Morinus options, including VIII=4 and IX=5;
- day ruler +7, hour ruler +6;
- superior-planet phase score uses the directional Morinus bands 18–30 / 30–40 / 40–80 / 80–100 / 100–120 with weights 1/2/3/2/1.

`AlmutenResult` and `AccidentalScores` are typed result objects while retaining mapping compatibility where older output code still needs it.

### Natal synthesis boundary

The program distinguishes reproducible calculation from interpretation.

Automatic or formal calculations include:
- temperament;
- duads;
- Lots;
- planetary day/hour;
- reception/generosity/repulsion and other formal relationship states;
- Almuten Figuris;
- composite Almuten of Mind;
- Ruler of Behaviour where the course gives a decisive hierarchy.

Evidence is collected without forcing a verdict where qualitative comparison is required:
- Primary Motivation;
- ambiguous Ruler-of-Behaviour cases;
- Ruler of Geniture;
- Quality-of-Mind synthesis.

The application deliberately does not try to automate full interpretive judgments such as physical appearance, triplicity life divisions, or topic-specific natal readings.

### Presentation — `hor_tools/rendering/`, `hor_tools/output.py`

Presentation is now layered:

- `rendering/technical.py`: compact terminal technical summary;
- `rendering/pretty_report.py`: complete polished Markdown and responsive standalone HTML reports;
- `rendering/almuten.py`: Almuten presentation;
- `rendering/relationships.py`: relationship-table presentation;
- `output.py`: legacy/full terminal and compatibility rendering used where still useful.

The normal CLI prints the compact terminal summary, automatically writes a complete Markdown report, and optionally writes the complete HTML report.

The Markdown/HTML renderers consume calculation results; they do not determine astrological doctrine.

### Commands — `hor_tools/cli.py`, `hor_tools/commands/`

Installed console commands:

- `hor-reader` — read one `.hor` chart, print the compact snapshot, and export complete reports;
- `hor-scan-events` — ingress/exact-aspect scanner using the lightweight longitude API;
- `hor-scan-asc` — Ascendant-sign-window reports with optional IANA timezone support.

The old root `scan_events.py` and `asc_window_scan.py` files remain compatibility wrappers only.

Testing and packaging
---------------------

`pyproject.toml` uses setuptools package discovery for `hor_tools*`, so `analysis`, `commands`, and `rendering` subpackages are included in built distributions.

Runtime dependencies are separate from development dependencies. Pytest, Ruff and build tooling live in the dev dependency group.

Permanent CI (`.github/workflows/ci.yml`) performs:

- dependency installation;
- correctness-oriented Ruff checks;
- the full pytest suite;
- package build;
- installation of the built wheel into a clean virtual environment;
- imports of important package submodules;
- `--help` / `--version` smoke tests for installed commands.

The clean-wheel step is intentional: an editable source checkout can hide missing-package configuration.

Domain invariants worth protecting
----------------------------------

- Traditional planets only.
- Tropical zodiac.
- Whole Sign house placement.
- Teacher-supplied private planetary aspect orbs remain project overrides.
- Aspect existence follows the course's sign-configuration/out-of-sign rule, not unrestricted geometric closeness.
- True astronomical horizon determines sect.
- Apparent sunrise/sunset is used for planetary-hour division, not as a replacement sect rule.
- Duad-to-Asc contact uses the project rule of 5°.
- Almuten scoring follows the teacher's actual Morinus configuration.
- A technique should not be made algorithmic when its source requires qualitative astrological judgment.
- Calculation code should fail explicitly when unsupported input would otherwise require guessing.

Future engineering work
-----------------------

Future work should be driven by concrete requirements rather than general refactoring:

- add representative anonymized Morinus fixtures when new real file variants are encountered;
- add native support for Julian/BC/local-apparent Morinus inputs only after reproducing Morinus conversion semantics exactly;
- add new natal techniques only when the rule can be sourced, reproduced, and tested;
- keep presentation improvements isolated from calculation doctrine.
