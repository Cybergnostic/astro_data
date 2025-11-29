from __future__ import annotations

from .models import PlanetPosition, SynodicPhaseInfo

# Small orb used for cazimi (17 arcminutes ≈ 0.2833°)
CAZIMI_ORB_DEG = 17.0 / 60.0

# Threshold for considering a planet stationary by daily speed in longitude.
STATION_THRESHOLD = 0.02

SUPERIOR_COMBUST_ORB = {
    "Saturn": 6.0,
    "Jupiter": 6.0,
    "Mars": 10.0,
}

SUPERIOR_UNDER_BEAMS_ORB = {
    "Saturn": 15.0,
    "Jupiter": 15.0,
    "Mars": 18.0,
}


def compute_elongation_and_orientation(planet_long: float, sun_long: float) -> tuple[float, bool, bool]:
    """
    Returns (elongation_deg, is_oriental, is_occidental).

    - elongation_deg: minimal angular distance from Sun, 0 - 180°
    - is_oriental: True if planet is behind the Sun in zodiacal order (rises before Sun)
    - is_occidental: True if planet is ahead of the Sun in zodiacal order (sets after Sun)
    """
    delta = (sun_long - planet_long) % 360.0
    if delta == 0.0:
        return 0.0, False, False
    elong = delta if delta <= 180.0 else 360.0 - delta
    is_oriental = 0 < delta < 180.0
    is_occidental = not is_oriental
    return elong, is_oriental, is_occidental


def motion_flags(speed_long: float) -> tuple[bool, bool, bool]:
    is_direct = speed_long > 0
    is_retro = speed_long < 0
    is_station = abs(speed_long) < STATION_THRESHOLD
    return is_direct, is_retro, is_station


def _phase(group: str, code: str, index: int, label: str) -> SynodicPhaseInfo:
    return SynodicPhaseInfo(group=group, code=code, index=index, label=label)


def compute_superior_synodic_phase(planet: PlanetPosition, sun_long: float) -> SynodicPhaseInfo:
    """
    Classify Saturn, Jupiter or Mars into a synodic phase bucket.

    Uses:
      - cazimi orb (~0.27°)
      - combust / under-beams orbs:
          Saturn/Jupiter: combust <=6°, under beams 6 - 15°
          Mars: combust <=10°, under beams 10 - 18°
      - oriental vs occidental orientation
      - direct / retro / station status
      - rough band markers at 60°, 90°, ~168° (opposition), 22°/18°, 15°
    """
    elong, is_oriental, _ = compute_elongation_and_orientation(planet.longitude, sun_long)
    is_direct, is_retro, is_station = motion_flags(planet.speed_long)
    combust_orb = SUPERIOR_COMBUST_ORB.get(planet.name, 6.0)
    under_orb = SUPERIOR_UNDER_BEAMS_ORB.get(planet.name, 15.0)

    if elong <= CAZIMI_ORB_DEG:
        return _phase("superior", "cazimi", 1, "Cazimi")

    if is_oriental:
        if elong <= combust_orb:
            return _phase("superior", "combust_east", 2, "Combust (east)")
        if elong <= under_orb:
            return _phase("superior", "under_beams_east", 3, "Under beams (east)")
        if is_station:
            return _phase("superior", "first_station", 7, "First station (east)")
        if is_retro:
            ahead_from_sun = (planet.longitude - sun_long) % 360.0
            if elong >= 168.0:
                return _phase("superior", "around_opposition", 9, "Around opposition")
            if ahead_from_sun > 180.0 and elong > 120.0:
                return _phase("superior", "retrograde_receding_or_pre_second_station", 10, "Retrograde receding / pre-second station")
            return _phase("superior", "retrograde_approaching_opposition", 8, "Retrograde approaching opposition")
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

    # Occidental side
    if elong <= combust_orb:
        return _phase("superior", "combust_west", 17, "Combust (west)")
    if elong <= under_orb:
        return _phase("superior", "under_beams_west", 16, "Under beams (west)")
    if is_station:
        return _phase("superior", "second_station", 11, "Second station (west)")
    if is_retro:
        if elong >= 168.0:
            return _phase("superior", "around_opposition", 9, "Around opposition")
        return _phase("superior", "retrograde_receding_or_pre_second_station", 10, "Retrograde receding / pre-second station")

    # Direct, occidental
    setting_threshold = 22.0 if planet.name in {"Saturn", "Jupiter"} else 18.0
    if elong < setting_threshold:
        return _phase("superior", "occidental_setting_degrees", 15, "Occidental setting degrees")
    if elong < 60.0:
        return _phase("superior", "occidental_visible_direct_early", 12, "Occidental visible (direct, early)")
    if elong < 90.0:
        return _phase("superior", "occidental_leaning", 13, "Occidental leaning")
    return _phase("superior", "occidental_strong", 14, "Occidental strong")


def compute_inferior_synodic_phase(planet: PlanetPosition, sun_long: float) -> SynodicPhaseInfo:
    """
    Classify Venus or Mercury into a synodic phase bucket.

    Uses:
      - cazimi orb
      - combust orb 7°
      - under-beams bands (east: 7-12°, west: 7-15°)
      - oriental vs occidental
      - direct / retro / station
    """
    elong, is_oriental, _ = compute_elongation_and_orientation(planet.longitude, sun_long)
    is_direct, is_retro, is_station = motion_flags(planet.speed_long)

    combust_orb = 7.0
    under_east = 15.0
    under_west = 15.0

    if elong <= CAZIMI_ORB_DEG:
        return _phase("inferior", "cazimi", 1, "Cazimi")

    if is_oriental:
        if is_retro:
            if elong <= combust_orb:
                return _phase("inferior", "combust_east_return", 8, "Combust (east, return)")
            if elong <= under_east:
                return _phase("inferior", "under_beams_east_return", 7, "Under beams (east, return)")
            if is_station:
                return _phase("inferior", "second_station_east", 5, "Second station (east)")
            return _phase("inferior", "direct_east_closing", 6, "Direct east closing")
        if elong <= combust_orb:
            return _phase("inferior", "combust_east", 2, "Combust (east)")
        if elong <= under_east:
            return _phase("inferior", "under_beams_east", 3, "Under beams (east)")
        if is_station:
            return _phase("inferior", "second_station_east", 5, "Second station (east)")
        # Direct, oriental
        return _phase("inferior", "oriental_strong_before_second_station", 4, "Oriental strong (before station)")

    # Occidental side
    if elong <= CAZIMI_ORB_DEG:
        return _phase("inferior", "cazimi_return", 9, "Cazimi (return)")
    if elong <= combust_orb:
        code = "combust_west" if is_direct else "combust_west_return"
        index = 10 if is_direct else 16
        label = "Combust (west)" if is_direct else "Combust (west, return)"
        return _phase("inferior", code, index, label)
    if elong <= under_west:
        code = "under_beams_west_7_15" if is_direct else "under_beams_west_15_7_return"
        index = 11 if is_direct else 15
        label = "Under beams (west 7-15)" if is_direct else "Under beams (west 15-7 return)"
        return _phase("inferior", code, index, label)
    if is_station:
        return _phase("inferior", "first_station_west", 13, "First station (west)")
    if is_retro:
        return _phase("inferior", "retrograde_west_towards_sun", 14, "Retrograde west towards Sun")
    return _phase("inferior", "occidental_visible_direct", 12, "Occidental visible (direct)")


def compute_lunar_synodic_phase(moon: PlanetPosition, sun_long: float) -> SynodicPhaseInfo:
    """
    Classify the Moon’s synodic phase using elongation bands from the Sun.
    """
    elong, _, _ = compute_elongation_and_orientation(moon.longitude, sun_long)
    waxing = ((moon.longitude - sun_long) % 360.0) < 180.0
    waning = not waxing

    if elong <= CAZIMI_ORB_DEG:
        return _phase("lunar", "cazimi", 1, "Cazimi")

    if waxing:
        if elong <= 6.0:
            return _phase("lunar", "combust", 2, "Combust")
        if elong <= 12.0:
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

    if waning:
        if elong <= 6.0:
            return _phase("lunar", "combust_west", 14, "Combust (west)")
        if elong <= 12.0:
            return _phase("lunar", "under_beams_west", 13, "Under beams (west)")
        if elong <= 45.0:
            return _phase("lunar", "waning_crescent", 12, "Waning crescent")
        if elong <= 90.0:
            return _phase("lunar", "waning_quarter", 11, "Waning quarter")
        if elong <= 135.0:
            return _phase("lunar", "waning_gibbous", 10, "Waning gibbous")
        return _phase("lunar", "waning_near_full", 9, "Waning near full")

    return _phase("lunar", "full", 8, "Full")
