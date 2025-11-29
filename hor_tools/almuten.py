from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
import math
from typing import Dict, List, Tuple

import swisseph as swe

from .analysis.dignity import SIGNS, TRIPLICITIES, essential_dignity, degree_in_sign, sign_index_from_longitude
from .analysis.sect import chart_sect
from .astro_engine import EPHE_PATH, julian_day_from_chart
from .models import ChartInput, Houses, PlanetPosition

CHALDEAN_ORDER = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]
ALMUTEN_PLANETS = CHALDEAN_ORDER

HOUSE_STRENGTH_ORDER = [1, 10, 7, 4, 11, 5, 2, 8, 9, 3, 12, 6]
HOUSE_STRENGTH_SCORES = {house: score for house, score in zip(HOUSE_STRENGTH_ORDER, range(12, 0, -1))}

DAY_RULERS = {
    0: "Moon",
    1: "Mars",
    2: "Mercury",
    3: "Jupiter",
    4: "Venus",
    5: "Saturn",
    6: "Sun",
}

ESSENTIAL_WEIGHTS = {
    "dom": 5,
    "exalt": 4,
    "trip": 3,
    "term": 2,
    "face": 1,
}


def _parse_hhmmss(s: str) -> time:
    h, m, sec = s.split(":")
    return time(int(h), int(m), int(sec))


def planetary_hour_from_local(birth_str: str, sunrise_str: str, sunset_str: str, day_ruler: str) -> str:
    """
    Reference implementation for planetary hours using pure local clock times.

    Args:
        birth_str: local birth time HH:MM:SS
        sunrise_str: local sunrise time HH:MM:SS
        sunset_str: local sunset time HH:MM:SS
        day_ruler: name of weekday ruler (e.g. "Venus" for Friday)
    """
    base_date = datetime(2000, 1, 1)

    def dt(t: time) -> datetime:
        return base_date.replace(hour=t.hour, minute=t.minute, second=t.second)

    birth = dt(_parse_hhmmss(birth_str))
    sunrise = dt(_parse_hhmmss(sunrise_str))
    sunset = dt(_parse_hhmmss(sunset_str))

    day_length = sunset - sunrise
    hour_len = day_length / 12
    hours_since_sunrise = int((birth - sunrise) / hour_len)
    hours_since_sunrise = max(0, min(hours_since_sunrise, 11))

    start_idx = CHALDEAN_ORDER.index(day_ruler)
    return CHALDEAN_ORDER[(start_idx + hours_since_sunrise) % len(CHALDEAN_ORDER)]


@dataclass
class EssentialRow:
    name: str
    longitude: float
    contributions: Dict[str, List[int]]
    totals: Dict[str, int]
    winners: List[str]


def get_essential_dignities_at_degree(longitude: float, is_day_chart: bool) -> Dict[str, Dict[str, bool]]:
    """
    For a given longitude, return per-planet dignity flags.
    """
    flags: Dict[str, Dict[str, bool]] = {}
    for planet in ALMUTEN_PLANETS:
        ess = essential_dignity(planet, longitude, is_day_chart=is_day_chart)
        flags[planet] = {
            "dom": ess["is_domicile"],
            "exalt": ess["is_exalted"],
            "trip": ess["triplicity_lord"] == planet,
            "term": ess["term_lord"] == planet,
            "face": ess["face_lord"] == planet,
        }
    return flags


def essential_contributions_at_degree(longitude: float, is_day_chart: bool) -> Dict[str, List[int]]:
    """Return per-planet contribution list of point weights."""
    flags = get_essential_dignities_at_degree(longitude, is_day_chart)
    sign_idx = sign_index_from_longitude(longitude)
    element = "fire" if sign_idx in {0, 4, 8} else "earth" if sign_idx in {1, 5, 9} else "air" if sign_idx in {2, 6, 10} else "water"
    trip_day, trip_night, trip_part = TRIPLICITIES[element]
    contributions: Dict[str, List[int]] = {}
    for planet, vals in flags.items():
        contribs: List[int] = []
        for key, weight in ESSENTIAL_WEIGHTS.items():
            if key == "trip":
                if planet in {trip_day, trip_night, trip_part}:
                    contribs.append(weight)
            elif vals.get(key):
                contribs.append(weight)
        contributions[planet] = contribs
    return contributions


def part_of_fortune_longitude(asc_long: float, sun_long: float, moon_long: float, sect_chart: str) -> float:
    if sect_chart == "day":
        fortune = asc_long + moon_long - sun_long
    else:
        fortune = asc_long + sun_long - moon_long
    return fortune % 360.0


def compute_syzygy_longitude(chart: ChartInput, sect_chart: str) -> float:
    """
    Approximate previous syzygy (new or full) longitude.

    Syzygy is the last exact lunation (conjunction or opposition) BEFORE birth.
    - If conjunction (new), both luminaries share longitude -> return that.
    - If opposition (full), return the longitude of the luminary that is above the horizon
      in the syzygy chart (the in-sect luminary for that syzygy moment).
    """

    swe.set_ephe_path(EPHE_PATH)
    start_jd = julian_day_from_chart(chart)

    def _sun_moon_diff(jd: float) -> float:
        sun_pos = swe.calc_ut(jd, swe.SUN)[0]
        moon_pos = swe.calc_ut(jd, swe.MOON)[0]
        sun_long = float(sun_pos[0])
        moon_long = float(moon_pos[0])
        return (moon_long - sun_long) % 360.0

    def _phase_distance(diff: float, target: float) -> float:
        return min((diff - target) % 360.0, (target - diff) % 360.0)

    def _find_previous_phase(target: float) -> float:
        best_jd = start_jd
        best_dist = _phase_distance(_sun_moon_diff(start_jd), target)
        last_dist = best_dist
        jd = start_jd
        # coarse backward walk ~40 days
        for _ in range(160):
            jd -= 0.25
            dist = _phase_distance(_sun_moon_diff(jd), target)
            if dist <= best_dist:
                best_dist = dist
                best_jd = jd
            elif dist > last_dist and best_jd < start_jd:
                break  # passed the minimum
            last_dist = dist

        # refine around best_jd
        for step in (0.1, 0.01, 0.001):
            improved = True
            while improved:
                improved = False
                for direction in (-step, step):
                    cand = best_jd + direction
                    dist = _phase_distance(_sun_moon_diff(cand), target)
                    if dist < best_dist and cand <= start_jd:
                        best_dist = dist
                        best_jd = cand
                        improved = True
                        break
        return best_jd

    new_jd = _find_previous_phase(0.0)
    full_jd = _find_previous_phase(180.0)

    if new_jd >= full_jd:
        jd_syzygy = new_jd
        syzygy_type = "new"
    else:
        jd_syzygy = full_jd
        syzygy_type = "full"

    sun_pos = swe.calc_ut(jd_syzygy, swe.SUN)[0]
    moon_pos = swe.calc_ut(jd_syzygy, swe.MOON)[0]
    sun_long = float(sun_pos[0]) % 360.0
    moon_long = float(moon_pos[0]) % 360.0

    if syzygy_type == "new":
        return sun_long

    # Full Moon: choose luminary above horizon in syzygy chart.
    def _altitude(body: int) -> float:
        # Use equatorial coords to compute true altitude above horizon.
        res = swe.calc_ut(jd_syzygy, body, swe.FLG_SWIEPH | swe.FLG_EQUATORIAL)
        equ = res[0] if isinstance(res[0], (list, tuple)) else res
        if len(equ) < 3:
            raise RuntimeError("Swiss Ephemeris did not return RA/Dec for altitude computation.")
        ra, dec = float(equ[0]), float(equ[1])
        lst = swe.sidtime(jd_syzygy) * 15.0  # degrees
        ha = (lst + chart.longitude - ra) % 360.0
        ha_rad = math.radians(ha)
        dec_rad = math.radians(dec)
        lat_rad = math.radians(chart.latitude)
        alt = math.degrees(
            math.asin(math.sin(dec_rad) * math.sin(lat_rad) + math.cos(dec_rad) * math.cos(lat_rad) * math.cos(ha_rad))
        )
        return alt

    sun_alt = _altitude(swe.SUN)
    moon_alt = _altitude(swe.MOON)
    if sun_alt > 0 and moon_alt <= 0:
        return sun_long
    if moon_alt > 0 and sun_alt <= 0:
        return moon_long

    # fallback: pick sect luminary for syzygy chart using house-based sect
    cusps, ascmc = swe.houses_ex(jd_syzygy, chart.latitude, chart.longitude, b"P")
    asc_sign = int(float(ascmc[0]) // 30)
    sun_house = ((int(sun_long // 30) - asc_sign) % 12) + 1
    moon_house = ((int(moon_long // 30) - asc_sign) % 12) + 1
    syz_sect = chart_sect(sun_house)
    return sun_long if syz_sect == "day" else moon_long


def build_essential_rows(chart: ChartInput, planets: List[PlanetPosition], houses: Houses) -> Tuple[List[EssentialRow], Dict[str, int], Dict[str, int]]:
    sun = next(p for p in planets if p.name == "Sun")
    moon = next(p for p in planets if p.name == "Moon")
    sect_chart = chart_sect(sun.house)

    fortune_long = part_of_fortune_longitude(houses.asc, sun.longitude, moon.longitude, sect_chart)
    syzygy_long = compute_syzygy_longitude(chart, sect_chart)

    points = [
        ("Sun", sun.longitude),
        ("Moon", moon.longitude),
        ("Asc", houses.asc),
        ("Fortune", fortune_long),
        ("Syzygy", syzygy_long),
    ]

    rows: List[EssentialRow] = []
    total_shares = {p: 0 for p in ALMUTEN_PLANETS}
    total_scores = {p: 0 for p in ALMUTEN_PLANETS}

    for name, lon in points:
        contribs = essential_contributions_at_degree(lon, sect_chart == "day")
        totals = {planet: sum(vals) for planet, vals in contribs.items()}
        max_score = max(totals.values()) if totals else 0
        winners = [p for p, score in totals.items() if score == max_score and score > 0]
        for p, score in totals.items():
            total_scores[p] += score
        for planet, vals in contribs.items():
            total_shares[planet] += len(vals)
        rows.append(EssentialRow(name=name, longitude=lon, contributions=contribs, totals=totals, winners=winners))

    return rows, total_shares, total_scores


def _sunrise_sunset(jd: float, lat: float, lon: float) -> Tuple[float, float]:
    """Return UT Julian days for sunrise and sunset around the given UT base JD."""
    swe.set_ephe_path(EPHE_PATH)
    rise_flag, rise_tret = swe.rise_trans(
        jd,
        swe.SUN,
        rsmi=swe.CALC_RISE | swe.BIT_DISC_CENTER | swe.BIT_NO_REFRACTION,
        geopos=(lon, lat, 0.0),
    )
    set_flag, set_tret = swe.rise_trans(
        jd,
        swe.SUN,
        rsmi=swe.CALC_SET | swe.BIT_DISC_CENTER | swe.BIT_NO_REFRACTION,
        geopos=(lon, lat, 0.0),
    )

    if rise_flag < 0 or not rise_tret:
        raise RuntimeError(f"Failed to compute sunrise for jd={jd}, lat={lat}, lon={lon}")
    if set_flag < 0 or not set_tret:
        raise RuntimeError(f"Failed to compute sunset for jd={jd}, lat={lat}, lon={lon}")

    # rise_jd = float(rise_tret[0])
    # set_jd = float(set_tret[0])
    return float(rise_tret[0]), float(set_tret[0])


def planetary_day_hour_rulers(chart: ChartInput) -> Tuple[str, str]:
    """Return (day_ruler, hour_ruler) for the birth moment."""
    dt_utc = chart.datetime_utc
    # Normalise to naive UTC for JD calculations
    if dt_utc.tzinfo is not None:
        dt_utc = dt_utc.astimezone(timezone.utc).replace(tzinfo=None)

    # Local civil time - same convention as Morinus (local clock with DST applied)
    dt_local = dt_utc + timedelta(hours=chart.tz_offset_hours)

    birth_jd = julian_day_from_chart(chart)

    # Local civil midnight of the birth day, then convert that to UT
    local_midnight = dt_local.replace(hour=0, minute=0, second=0, microsecond=0)
    utc_midnight = local_midnight - timedelta(hours=chart.tz_offset_hours)
    base_jd = swe.julday(
        utc_midnight.year,
        utc_midnight.month,
        utc_midnight.day,
        utc_midnight.hour
        + utc_midnight.minute / 60.0
        + utc_midnight.second / 3600.0,
        swe.GREG_CAL,
    )

    # Sunrise/sunset for current, previous, next local civil dates (all JDs in UT)
    sunrise_today, sunset_today = _sunrise_sunset(base_jd, chart.latitude, chart.longitude)
    sunrise_prev, sunset_prev = _sunrise_sunset(base_jd - 1, chart.latitude, chart.longitude)
    sunrise_next, sunset_next = _sunrise_sunset(base_jd + 1, chart.latitude, chart.longitude)

    # Determine planetary day and hours since sunrise (0 - 23)
    if sunrise_today <= birth_jd <= sunset_today:
        # Daytime of current planetary day
        planetary_weekday = dt_local.weekday()
        day_ruler_name = DAY_RULERS[planetary_weekday]

        day_length = sunset_today - sunrise_today
        hour_len_day = day_length / 12.0 if day_length > 0 else 0.0
        hours_since_sunrise = int((birth_jd - sunrise_today) / hour_len_day) if hour_len_day else 0

    elif birth_jd > sunset_today:
        # Night after today's sunset - same planetary day
        planetary_weekday = dt_local.weekday()
        day_ruler_name = DAY_RULERS[planetary_weekday]

        night_length = sunrise_next - sunset_today
        hour_len_night = night_length / 12.0 if night_length > 0 else 0.0
        night_hours_since_sunset = int((birth_jd - sunset_today) / hour_len_night) if hour_len_night else 0
        hours_since_sunrise = 12 + night_hours_since_sunset

    else:
        # Night before today's sunrise - previous planetary day
        prev_local = dt_local - timedelta(days=1)
        planetary_weekday = prev_local.weekday()
        day_ruler_name = DAY_RULERS[planetary_weekday]

        night_length_prev = sunrise_today - sunset_prev
        hour_len_night_prev = night_length_prev / 12.0 if night_length_prev > 0 else 0.0
        night_hours_since_prev_sunset = int((birth_jd - sunset_prev) / hour_len_night_prev) if hour_len_night_prev else 0
        hours_since_sunrise = 12 + night_hours_since_prev_sunset

    # Clamp for safety
    hours_since_sunrise = max(0, min(hours_since_sunrise, 23))

    start_idx = CHALDEAN_ORDER.index(day_ruler_name)
    hour_ruler_name = CHALDEAN_ORDER[(start_idx + hours_since_sunrise) % len(CHALDEAN_ORDER)]

    return day_ruler_name, hour_ruler_name



def phase_score(planet: PlanetPosition, sun_longitude: float) -> int:
    """
    Ezra-style phase scoring for superior planets (Mars/Jupiter/Saturn).

    - Only applies to superior planets.
    - Requires direct motion (speed_long > 0).
    - Uses minimal elongation from the Sun (0-180°):
        15°-60°  => 3 points
        61°-90°  => 2 points
        91°+     => 1 point
        otherwise -> 0
    """
    if planet.name not in {"Saturn", "Jupiter", "Mars"}:
        return 0
    if planet.speed_long <= 0:
        return 0

    diff = (planet.longitude - sun_longitude) % 360.0
    elong = diff if diff <= 180.0 else 360.0 - diff

    if 15.0 <= elong <= 60.0:
        return 3
    if 61.0 <= elong <= 90.0:
        return 2
    if elong >= 91.0:
        return 1
    return 0


def compute_accidental_scores(chart: ChartInput, planets: List[PlanetPosition]) -> Dict[str, Dict[str, int | str]]:
    house_scores = {p.name: HOUSE_STRENGTH_SCORES.get(p.house, 0) for p in planets}
    day_ruler, hour_ruler = planetary_day_hour_rulers(chart)
    day_bonus = {planet: 7 if planet == day_ruler else 0 for planet in ALMUTEN_PLANETS}
    hour_bonus = {planet: 6 if planet == hour_ruler else 0 for planet in ALMUTEN_PLANETS}
    sun = next(p for p in planets if p.name == "Sun")
    phase_scores = {p.name: phase_score(p, sun.longitude) for p in planets}

    accidental_totals = {
        planet: house_scores.get(planet, 0)
        + day_bonus.get(planet, 0)
        + hour_bonus.get(planet, 0)
        + phase_scores.get(planet, 0)
        for planet in ALMUTEN_PLANETS
    }

    return {
        "house_scores": house_scores,
        "day_ruler": day_ruler,
        "hour_ruler": hour_ruler,
        "day_bonus": day_bonus,
        "hour_bonus": hour_bonus,
        "phase_scores": phase_scores,
        "accidental_totals": accidental_totals,
    }


def build_almuten_figuris(chart: ChartInput, planets: List[PlanetPosition], houses: Houses) -> Dict[str, object]:
    rows, total_shares, total_scores = build_essential_rows(chart, planets, houses)
    accidental = compute_accidental_scores(chart, planets)

    essential_totals = total_scores
    accidental_totals = accidental["accidental_totals"]
    grand_scores = {p: essential_totals.get(p, 0) + accidental_totals.get(p, 0) for p in ALMUTEN_PLANETS}
    max_score = max(grand_scores.values()) if grand_scores else 0
    almuten = [p for p, score in grand_scores.items() if score == max_score]

    return {
        "rows": rows,
        "total_shares": total_shares,
        "essential_totals": essential_totals,
        "accidental": accidental,
        "grand_scores": grand_scores,
        "almuten": almuten,
        "almuten_score": max_score,
    }
