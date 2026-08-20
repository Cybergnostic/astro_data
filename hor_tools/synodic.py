from __future__ import annotations

from .models import PlanetPosition, SynodicPhaseInfo

# Course solar-contact thresholds.
CAZIMI_ORB_DEG = 17.0 / 60.0
COMBUST_ORB_DEG = 7.5
UNDER_BEAMS_ORB_DEG = 15.0

# Kept only as a backwards-compatible exact-zero fallback for manually-created
# PlanetPosition objects. Real chart calculations set PlanetPosition.station by
# comparing signed motion on adjacent ephemeris days.
EXACT_STATION_EPSILON = 1e-9


def _minimal_separation(a: float, b: float) -> float:
    diff = abs((a - b) % 360.0)
    return min(diff, 360.0 - diff)


def is_true_cazimi(
    planet: PlanetPosition,
    sun: PlanetPosition,
    orb_deg: float = CAZIMI_ORB_DEG,
) -> bool:
    """Return the stricter two-dimensional cazimi condition.

    Ordinary course/Lilly-style cazimi uses <=17 arcminutes in ecliptic
    longitude. The stricter medieval condition associated especially with
    Bonatti also requires the planet to be within the same narrow distance in
    ecliptic latitude from the Sun. Bonatti's surviving wording is commonly
    translated as 16 arcminutes; this project defaults to the teacher/course
    17-minute cazimi limit for both coordinates, while allowing callers to
    supply another orb explicitly.
    """
    if planet.name == "Sun":
        return False
    longitude_close = _minimal_separation(planet.longitude, sun.longitude) <= orb_deg
    latitude_close = abs(planet.latitude - sun.latitude) <= orb_deg
    return longitude_close and latitude_close


def compute_elongation_and_orientation(planet_long: float, sun_long: float) -> tuple[float, bool, bool]:
    """Return (elongation, oriental, occidental) relative to the Sun."""
    delta = (sun_long - planet_long) % 360.0
    if delta == 0.0:
        return 0.0, False, False
    elong = delta if delta <= 180.0 else 360.0 - delta
    is_oriental = 0 < delta < 180.0
    is_occidental = not is_oriental
    return elong, is_oriental, is_occidental


def motion_flags(
    speed_long: float, station_phase: str | None = None
) -> tuple[bool, bool, bool]:
    """Return direct/retrograde/station flags.

    Real ephemeris positions supply ``station_phase`` from an adjacent-day
    reversal check. Exact zero remains a narrow fallback for synthetic callers
    and tests; it is not used as a practical station threshold.
    """
    is_station = station_phase in {"first", "second"} or abs(speed_long) <= EXACT_STATION_EPSILON
    is_direct = not is_station and speed_long > 0.0
    is_retro = not is_station and speed_long < 0.0
    return is_direct, is_retro, is_station


def _phase(group: str, code: str, index: int, label: str) -> SynodicPhaseInfo:
    return SynodicPhaseInfo(group=group, code=code, index=index, label=label)


def compute_superior_synodic_phase(planet: PlanetPosition, sun_long: float) -> SynodicPhaseInfo:
    """Classify Saturn, Jupiter or Mars into a traditional synodic phase bucket."""
    elong, is_oriental, _ = compute_elongation_and_orientation(planet.longitude, sun_long)
    is_direct, is_retro, is_station = motion_flags(planet.speed_long, planet.station)

    if elong <= CAZIMI_ORB_DEG:
        return _phase("superior", "cazimi", 1, "Cazimi")

    if is_oriental:
        if elong <= COMBUST_ORB_DEG:
            return _phase("superior", "combust_east", 2, "Combust (east)")
        if elong <= UNDER_BEAMS_ORB_DEG:
            return _phase("superior", "under_beams_east", 3, "Under beams (east)")
        if is_station:
            label = "First station (east)" if planet.station != "second" else "Second station (east)"
            code = "first_station" if planet.station != "second" else "second_station"
            index = 7 if planet.station != "second" else 11
            return _phase("superior", code, index, label)
        if is_retro:
            ahead_from_sun = (planet.longitude - sun_long) % 360.0
            if elong >= 168.0:
                return _phase("superior", "around_opposition", 9, "Around opposition")
            if ahead_from_sun > 180.0 and elong > 120.0:
                return _phase(
                    "superior",
                    "retrograde_receding_or_pre_second_station",
                    10,
                    "Retrograde receding / pre-second station",
                )
            return _phase(
                "superior",
                "retrograde_approaching_opposition",
                8,
                "Retrograde approaching opposition",
            )
        if is_direct:
            ahead_from_sun = (planet.longitude - sun_long) % 360.0
            if ahead_from_sun >= 300.0:
                return _phase("superior", "oriental_far_before_station", 6, "Oriental far before station")
            if elong <= 30.0:
                return _phase("superior", "oriental_strong", 4, "Oriental strong")
            if elong <= 90.0:
                return _phase("superior", "oriental_weak", 5, "Oriental weak")
            return _phase("superior", "oriental_far_before_station", 6, "Oriental far before station")
        return _phase("superior", "oriental_weak", 5, "Oriental weak")

    if elong <= COMBUST_ORB_DEG:
        return _phase("superior", "combust_west", 17, "Combust (west)")
    if elong <= UNDER_BEAMS_ORB_DEG:
        return _phase("superior", "under_beams_west", 16, "Under beams (west)")
    if is_station:
        label = "Second station (west)" if planet.station != "first" else "First station (west)"
        code = "second_station" if planet.station != "first" else "first_station"
        index = 11 if planet.station != "first" else 7
        return _phase("superior", code, index, label)
    if is_retro:
        if elong >= 168.0:
            return _phase("superior", "around_opposition", 9, "Around opposition")
        return _phase(
            "superior",
            "retrograde_receding_or_pre_second_station",
            10,
            "Retrograde receding / pre-second station",
        )

    setting_threshold = 22.0 if planet.name in {"Saturn", "Jupiter"} else 18.0
    if elong < setting_threshold:
        return _phase("superior", "occidental_setting_degrees", 15, "Occidental setting degrees")
    if elong < 60.0:
        return _phase("superior", "occidental_visible_direct_early", 12, "Occidental visible (direct, early)")
    if elong < 90.0:
        return _phase("superior", "occidental_leaning", 13, "Occidental leaning")
    return _phase("superior", "occidental_strong", 14, "Occidental strong")


def compute_inferior_synodic_phase(planet: PlanetPosition, sun_long: float) -> SynodicPhaseInfo:
    """Classify Venus or Mercury into a synodic phase bucket."""
    elong, is_oriental, _ = compute_elongation_and_orientation(planet.longitude, sun_long)
    is_direct, is_retro, is_station = motion_flags(planet.speed_long, planet.station)

    if elong <= CAZIMI_ORB_DEG:
        return _phase("inferior", "cazimi", 1, "Cazimi")

    if is_oriental:
        if elong <= COMBUST_ORB_DEG:
            code = "combust_east_return" if is_retro else "combust_east"
            index = 8 if is_retro else 2
            label = "Combust (east, return)" if is_retro else "Combust (east)"
            return _phase("inferior", code, index, label)
        if elong <= UNDER_BEAMS_ORB_DEG:
            code = "under_beams_east_return" if is_retro else "under_beams_east"
            index = 7 if is_retro else 3
            label = "Under beams (east, return)" if is_retro else "Under beams (east)"
            return _phase("inferior", code, index, label)
        if is_station:
            station = planet.station or "second"
            if station == "first":
                return _phase("inferior", "first_station_east", 13, "First station (east)")
            return _phase("inferior", "second_station_east", 5, "Second station (east)")
        if is_retro:
            return _phase("inferior", "direct_east_closing", 6, "Retrograde east closing")
        return _phase(
            "inferior",
            "oriental_strong_before_second_station",
            4,
            "Oriental strong (before station)",
        )

    if elong <= COMBUST_ORB_DEG:
        code = "combust_west" if is_direct else "combust_west_return"
        index = 10 if is_direct else 16
        label = "Combust (west)" if is_direct else "Combust (west, return)"
        return _phase("inferior", code, index, label)
    if elong <= UNDER_BEAMS_ORB_DEG:
        code = "under_beams_west" if is_direct else "under_beams_west_return"
        index = 11 if is_direct else 15
        label = "Under beams (west)" if is_direct else "Under beams (west, return)"
        return _phase("inferior", code, index, label)
    if is_station:
        station = planet.station or "first"
        if station == "second":
            return _phase("inferior", "second_station_west", 5, "Second station (west)")
        return _phase("inferior", "first_station_west", 13, "First station (west)")
    if is_retro:
        return _phase("inferior", "retrograde_west_towards_sun", 14, "Retrograde west towards Sun")
    return _phase("inferior", "occidental_visible_direct", 12, "Occidental visible (direct)")


def compute_lunar_synodic_phase(moon: PlanetPosition, sun_long: float) -> SynodicPhaseInfo:
    """Classify the Moon's synodic phase while using the common solar-ray thresholds."""
    elong, _, _ = compute_elongation_and_orientation(moon.longitude, sun_long)
    waxing = ((moon.longitude - sun_long) % 360.0) < 180.0

    if elong <= CAZIMI_ORB_DEG:
        return _phase("lunar", "cazimi", 1, "Cazimi")

    if waxing:
        if elong <= COMBUST_ORB_DEG:
            return _phase("lunar", "combust", 2, "Combust")
        if elong <= UNDER_BEAMS_ORB_DEG:
            return _phase("lunar", "under_beams", 3, "Under beams")
        if elong <= 45.0:
            return _phase("lunar", "waxing_crescent", 4, "Waxing crescent")
        if elong <= 90.0:
            return _phase("lunar", "waxing_quarter", 5, "Waxing quarter")
        if elong <= 135.0:
            return _phase("lunar", "waxing_gibbous", 6, "Waxing gibbous")
        if elong <= 168.0:
            return _phase("lunar", "waxing_near_full", 7, "Waxing near full")
        return _phase("lunar", "full", 8, "Full")

    if elong <= COMBUST_ORB_DEG:
        return _phase("lunar", "combust_west", 14, "Combust (west)")
    if elong <= UNDER_BEAMS_ORB_DEG:
        return _phase("lunar", "under_beams_west", 13, "Under beams (west)")
    if elong <= 45.0:
        return _phase("lunar", "waning_crescent", 12, "Waning crescent")
    if elong <= 90.0:
        return _phase("lunar", "waning_quarter", 11, "Waning quarter")
    if elong <= 135.0:
        return _phase("lunar", "waning_gibbous", 10, "Waning gibbous")
    return _phase("lunar", "waning_near_full", 9, "Waning near full")
