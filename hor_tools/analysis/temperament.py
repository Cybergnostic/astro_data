"""Course temperament worksheet calculation.

The course scores four humoral outcomes (K/S/M/F) from a fixed set of
witnesses.  Some planetary phase entries state only one primal quality (for
example 'dry'); those testimonies therefore contribute to both temperaments
that contain that quality instead of silently inventing a second quality.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import swisseph as swe

from ..astro_engine import ensure_ephe_path, julian_day_from_chart
from ..models import ChartInput, Houses, PlanetPosition, PlanetReport
from .aspects import ASPECTS, _aspect_angle_for_contact, _distance_to_aspect
from .dignity import SIGNS, SIGN_RULERS, sign_index_from_longitude
from .duads import dodekatemorion_longitude
from .stars import COURSE_STARS, _resolve_star

ASC_CONTACT_ORB = 5.0  # user's working interpretation of the course's 4-5° range
MOON_CONTACT_ORB = 6.0  # user's working interpretation of the course's 5-6° range

TEMPERAMENTS = ("K", "S", "M", "F")
TEMPERAMENT_LABELS = {
    "K": "Choleric",
    "S": "Sanguine",
    "M": "Melancholic",
    "F": "Phlegmatic",
}
TEMPERAMENT_QUALITIES = {
    "K": {"hot", "dry"},
    "S": {"hot", "moist"},
    "M": {"cold", "dry"},
    "F": {"cold", "moist"},
}
SIGN_TEMPERAMENT = {
    0: "K", 1: "M", 2: "S", 3: "F",
    4: "K", 5: "M", 6: "S", 7: "F",
    8: "K", 9: "M", 10: "S", 11: "F",
}


@dataclass
class TemperamentRow:
    factor: str
    evidence: list[str] = field(default_factory=list)
    scores: dict[str, int] = field(
        default_factory=lambda: {key: 0 for key in TEMPERAMENTS}
    )
    note: str | None = None


@dataclass
class TemperamentReport:
    rows: list[TemperamentRow]
    totals: dict[str, int]
    dominant: list[str]


def _qualities_to_scores(qualities: set[str]) -> dict[str, int]:
    """Map complete or partial primal qualities to compatible temperaments."""

    if not qualities:
        return {key: 0 for key in TEMPERAMENTS}
    compatible = [
        key for key, pair in TEMPERAMENT_QUALITIES.items() if qualities <= pair
    ]
    return {key: int(key in compatible) for key in TEMPERAMENTS}


def _score_sign(longitude: float) -> dict[str, int]:
    winner = SIGN_TEMPERAMENT[sign_index_from_longitude(longitude)]
    return {key: int(key == winner) for key in TEMPERAMENTS}


def _planet_qualities(report: PlanetReport) -> set[str]:
    """Return the course table's phase-sensitive planetary qualities."""

    name = report.planet.name
    if name == "Sun":
        return {"hot", "dry"}
    if name == "Moon":
        return {"cold", "moist"}

    oriental = report.oriental
    if name == "Saturn":
        return {"cold", "dry"} if oriental else {"dry"}
    if name == "Jupiter":
        return {"hot", "moist"} if oriental else {"moist"}
    if name == "Mars":
        return {"hot", "dry"} if oriental else {"dry"}
    if name == "Venus":
        return {"hot", "moist"} if oriental else {"cold", "moist"}
    if name == "Mercury":
        return {"hot", "moist"} if oriental else {"cold", "dry"}
    return set()


def _merge_scores(target: dict[str, int], addition: dict[str, int]) -> None:
    for key in TEMPERAMENTS:
        target[key] += addition.get(key, 0)


def _add_sign(row: TemperamentRow, longitude: float, label: str) -> None:
    sign_idx = sign_index_from_longitude(longitude)
    _merge_scores(row.scores, _score_sign(longitude))
    row.evidence.append(f"{label}: {SIGNS[sign_idx]}")


def _add_planet_nature(row: TemperamentRow, report: PlanetReport, label: str) -> None:
    qualities = _planet_qualities(report)
    _merge_scores(row.scores, _qualities_to_scores(qualities))
    phase = "oriental" if report.oriental else "occidental"
    row.evidence.append(f"{label}: {report.planet.name} ({phase}; {', '.join(sorted(qualities))})")


def _contact(
    source_longitude: float, target_longitude: float, max_orb: float
) -> tuple[str, float] | None:
    angle = _aspect_angle_for_contact(source_longitude, target_longitude, max_orb)
    if angle is None:
        return None
    return ASPECTS[angle], _distance_to_aspect(source_longitude, target_longitude, angle)


def _score_aspect_witness(
    row: TemperamentRow,
    source: PlanetReport,
    target_longitude: float,
    max_orb: float,
) -> None:
    contact = _contact(source.planet.longitude, target_longitude, max_orb)
    if contact is None:
        return
    kind, orb = contact
    if kind == "conjunction":
        _add_planet_nature(row, source, f"{source.planet.name} conjunction {orb:.2f}°")
    else:
        _add_sign(row, source.planet.longitude, f"{source.planet.name} {kind} {orb:.2f}°")


def _lunar_phase_score(sun_longitude: float, moon_longitude: float) -> tuple[str, dict[str, int]]:
    arc = (moon_longitude - sun_longitude) % 360.0
    if arc < 90.0:
        key, label = "S", "New to First Quarter"
    elif arc < 180.0:
        key, label = "K", "First Quarter to Full"
    elif arc < 270.0:
        key, label = "M", "Full to Last Quarter"
    else:
        key, label = "F", "Last Quarter to New"
    return label, {code: int(code == key) for code in TEMPERAMENTS}


def _season_score(sun_longitude: float) -> tuple[str, dict[str, int]]:
    sign = sign_index_from_longitude(sun_longitude)
    if sign in {0, 1, 2}:
        key, label = "S", "Spring"
    elif sign in {3, 4, 5}:
        key, label = "K", "Summer"
    elif sign in {6, 7, 8}:
        key, label = "M", "Autumn"
    else:
        key, label = "F", "Winter"
    return label, {code: int(code == key) for code in TEMPERAMENTS}


def _node_longitudes(chart: ChartInput) -> tuple[float, float]:
    ensure_ephe_path()
    jd = julian_day_from_chart(chart)
    north = float(swe.calc_ut(jd, swe.TRUE_NODE, swe.FLG_SWIEPH)[0][0]) % 360.0
    return north, (north + 180.0) % 360.0


def _first_magnitude_stars_on_asc(chart: ChartInput, asc: float) -> list[str]:
    ensure_ephe_path()
    jd = julian_day_from_chart(chart)
    hits: list[str] = []
    for display, aliases in COURSE_STARS:
        resolved = _resolve_star(aliases, jd)
        if resolved is None:
            continue
        pos, magnitude = resolved
        if magnitude >= 1.5:
            continue
        diff = abs((float(pos[0]) - asc + 180.0) % 360.0 - 180.0)
        if diff <= 1.5:
            hits.append(f"{display} (mag {magnitude:.2f}, orb {diff:.2f}°)")
    return hits


def build_temperament(
    chart: ChartInput,
    planets: list[PlanetPosition],
    houses: Houses,
    reports: list[PlanetReport],
    almuten_name: str | None,
) -> TemperamentReport:
    """Build the complete auditable K/S/M/F worksheet."""

    by_name = {report.planet.name: report for report in reports}
    pos = {planet.name: planet for planet in planets}
    asc_ruler = SIGN_RULERS[sign_index_from_longitude(houses.asc)]
    asc_ruler_report = by_name[asc_ruler]
    moon = pos["Moon"]
    moon_report = by_name["Moon"]
    sun = pos["Sun"]

    rows: list[TemperamentRow] = []

    row = TemperamentRow("ASC")
    _add_sign(row, houses.asc, "Ascendant")
    rows.append(row)

    row = TemperamentRow("ASC ruler nature")
    _add_planet_nature(row, asc_ruler_report, asc_ruler)
    rows.append(row)

    row = TemperamentRow("ASC ruler sign")
    _add_sign(row, asc_ruler_report.planet.longitude, asc_ruler)
    rows.append(row)

    row = TemperamentRow("Aspects to ASC ruler")
    for report in reports:
        if report.planet.name == asc_ruler:
            continue
        _score_aspect_witness(row, report, asc_ruler_report.planet.longitude, ASC_CONTACT_ORB)
    rows.append(row)

    row = TemperamentRow("Planets and nodes in House I")
    for report in reports:
        if report.planet.house == 1:
            _add_planet_nature(row, report, report.planet.name)
    north, south = _node_longitudes(chart)
    asc_sign = sign_index_from_longitude(houses.asc)
    if sign_index_from_longitude(north) == asc_sign:
        _merge_scores(row.scores, {"K": 0, "S": 1, "M": 0, "F": 0})
        row.evidence.append("North Node in House I: sanguine")
    if sign_index_from_longitude(south) == asc_sign:
        _merge_scores(row.scores, {"K": 0, "S": 0, "M": 1, "F": 0})
        row.evidence.append("South Node in House I: melancholic")
    rows.append(row)

    row = TemperamentRow("Planetary duads / 1st-mag stars on ASC")
    for report in reports:
        duad = dodekatemorion_longitude(report.planet.longitude)
        diff = abs((duad - houses.asc + 180.0) % 360.0 - 180.0)
        if diff <= ASC_CONTACT_ORB:
            _add_planet_nature(row, report, f"{report.planet.name} duad on ASC ({diff:.2f}°)")
    stars = _first_magnitude_stars_on_asc(chart, houses.asc)
    if stars:
        row.evidence.extend(stars)
        row.note = (
            "First-magnitude star contacts are listed but not scored because the current "
            "machine catalogue does not yet encode each star's primary planetary nature."
        )
    rows.append(row)

    row = TemperamentRow("Aspects to ASC")
    for report in reports:
        _score_aspect_witness(row, report, houses.asc, ASC_CONTACT_ORB)
    rows.append(row)

    row = TemperamentRow("Lunar phase")
    phase_label, phase_scores = _lunar_phase_score(sun.longitude, moon.longitude)
    _merge_scores(row.scores, phase_scores)
    row.evidence.append(phase_label)
    rows.append(row)

    row = TemperamentRow("Moon sign")
    _add_sign(row, moon.longitude, "Moon")
    rows.append(row)

    row = TemperamentRow("Moon dispositor sign")
    moon_dispositor = SIGN_RULERS[sign_index_from_longitude(moon.longitude)]
    _add_sign(row, pos[moon_dispositor].longitude, moon_dispositor)
    rows.append(row)

    row = TemperamentRow("Moon aspects")
    for report in reports:
        if report.planet.name == "Moon":
            continue
        _score_aspect_witness(row, report, moon.longitude, MOON_CONTACT_ORB)
    rows.append(row)

    row = TemperamentRow("Season")
    season_label, season_scores = _season_score(sun.longitude)
    _merge_scores(row.scores, season_scores)
    row.evidence.append(season_label)
    rows.append(row)

    row = TemperamentRow("Almuten Figuris nature")
    if almuten_name and almuten_name in by_name:
        _add_planet_nature(row, by_name[almuten_name], almuten_name)
    else:
        row.note = "No unique Almuten Figuris available."
    rows.append(row)

    row = TemperamentRow("Almuten Figuris sign")
    if almuten_name and almuten_name in by_name:
        _add_sign(row, by_name[almuten_name].planet.longitude, almuten_name)
    else:
        row.note = "No unique Almuten Figuris available."
    rows.append(row)

    totals = {key: sum(row.scores[key] for row in rows) for key in TEMPERAMENTS}
    maximum = max(totals.values(), default=0)
    dominant = [TEMPERAMENT_LABELS[key] for key, value in totals.items() if value == maximum]
    return TemperamentReport(rows=rows, totals=totals, dominant=dominant)
