from __future__ import annotations

from .models import PlanetPosition, SynodicPhaseInfo

# Project-wide solar-contact thresholds used for report conditions.  The course
# contains author-specific visibility variants elsewhere, but this calculator
# deliberately keeps one common set for the named conditions.
CAZIMI_ORB_DEG = 17.0 / 60.0
COMBUST_ORB_DEG = 7.5
UNDER_BEAMS_ORB_DEG = 15.0

# Kept only as a backwards-compatible exact-zero fallback for manually-created
# PlanetPosition objects. Real chart calculations set PlanetPosition.station by
# comparing signed motion on adjacent ephemeris days.
EXACT_STATION_EPSILON = 1e-9
ANGLE_EPSILON = 1e-8


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
    """Return (elongation, oriental, occidental) relative to the Sun.

    For the traditional superior-planet cycle, ``oriental`` is the half from
    conjunction toward opposition in which the planet is behind the Sun in
    zodiacal order and rises before it.  ``occidental`` is the return half from
    opposition toward the next conjunction.
    """
    delta = (sun_long - planet_long) % 360.0
    if delta == 0.0:
        return 0.0, False, False
    elong = delta if delta <= 180.0 else 360.0 - delta
    is_oriental = 0.0 < delta < 180.0
    is_occidental = 180.0 < delta < 360.0
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
    """Classify Saturn, Jupiter or Mars through the course's 17-phase cycle."""
    elong, is_oriental, is_occidental = compute_elongation_and_orientation(
        planet.longitude, sun_long
    )
    is_direct, is_retro, is_station = motion_flags(planet.speed_long, planet.station)

    if elong <= CAZIMI_ORB_DEG:
        return _phase("superior", "cazimi", 1, "Cazimi")

    # Exact opposition is its own ninth phase.  Do not give it a broad invented
    # orb; neighbouring retrograde positions belong to phase 8 or 10.
    if abs(elong - 180.0) <= ANGLE_EPSILON:
        return _phase("superior", "opposition", 9, "Opposition to Sun")

    if is_oriental:
        if elong <= COMBUST_ORB_DEG:
            return _phase("superior", "combust_east", 2, "Combust (east)")
        if elong <= UNDER_BEAMS_ORB_DEG:
            return _phase("superior", "under_beams_east", 3, "Under beams (east)")

        if is_station:
            # A real superior on this half of the cycle is at the first station.
            # Keep the explicit field authoritative for synthetic/edge callers.
            if planet.station == "second":
                return _phase("superior", "second_station", 11, "Second station")
            return _phase("superior", "first_station", 7, "First station")

        if is_retro:
            return _phase(
                "superior",
                "retrograde_approaching_opposition",
                8,
                "Retrograde approaching opposition",
            )

        # Phases 4-6: strong easternization to 60°, weak to 90°, then the
        # remainder of the oriental/direct arc until the first station.
        if is_direct and elong <= 60.0:
            return _phase("superior", "oriental_strong", 4, "Strong easternization")
        if is_direct and elong <= 90.0:
            return _phase("superior", "oriental_weak", 5, "Weak easternization")
        return _phase(
            "superior",
            "oriental_far_before_station",
            6,
            "After easternization / before first station",
        )

    # Occidental return half: opposition -> second station -> direct return to Sun.
    if is_occidental:
        if elong <= COMBUST_ORB_DEG:
            return _phase("superior", "combust_west", 17, "Combust (west)")
        if elong <= UNDER_BEAMS_ORB_DEG:
            return _phase("superior", "under_beams_west", 16, "Under beams (west)")

        if is_station:
            if planet.station == "first":
                return _phase("superior", "first_station", 7, "First station")
            return _phase("superior", "second_station", 11, "Second station")

        if is_retro:
            return _phase(
                "superior",
                "retrograde_receding_or_pre_second_station",
                10,
                "Retrograde after opposition / before second station",
            )

        setting_threshold = 22.0 if planet.name in {"Saturn", "Jupiter"} else 18.0
        if is_direct and elong > 90.0:
            return _phase(
                "superior",
                "occidental_visible_direct_early",
                12,
                "Direct after second station",
            )
        if is_direct and elong > 60.0:
            return _phase("superior", "occidental_leaning", 13, "Leaning to westernization")
        if is_direct and elong >= setting_threshold:
            return _phase("superior", "occidental_strong", 14, "Westernization")
        return _phase(
            "superior",
            "occidental_setting_degrees",
            15,
            "Occidental setting degrees",
        )

    # Only exact conjunction/opposition can fall outside both orientation halves;
    # conjunction was caught by cazimi and opposition above. This is defensive.
    return _phase("superior", "opposition", 9, "Opposition to Sun")


def compute_inferior_synodic_phase(planet: PlanetPosition, sun_long: float) -> SynodicPhaseInfo:
    """Classify Venus or Mercury through the course's 16-phase cycle.

    On the oriental/eastern half, phases 2-4 occur while the inferior planet is
    retrograde after the inferior conjunction; after the second station it is
    direct (phase 6) and returns toward the Sun through phases 7-8.  The old
    implementation had those two motion branches reversed.
    """
    elong, is_oriental, is_occidental = compute_elongation_and_orientation(
        planet.longitude, sun_long
    )
    is_direct, is_retro, is_station = motion_flags(planet.speed_long, planet.station)

    if elong <= CAZIMI_ORB_DEG:
        # The course numbers the inferior and superior conjunctions differently,
        # but both are cazimi. With position alone we use phase 1 as cycle start.
        return _phase("inferior", "cazimi", 1, "Cazimi")

    if is_oriental:
        if is_station:
            if planet.station == "first":
                return _phase("inferior", "first_station_east", 13, "First station (east)")
            return _phase("inferior", "second_station_east", 5, "Second station (east)")

        if is_retro:
            if elong <= COMBUST_ORB_DEG:
                return _phase("inferior", "combust_east", 2, "Combust (east)")
            if elong <= UNDER_BEAMS_ORB_DEG:
                return _phase("inferior", "under_beams_east", 3, "Under beams (east)")
            return _phase(
                "inferior",
                "oriental_strong_before_second_station",
                4,
                "Strong easternization (before second station)",
            )

        # Direct after the second station, closing back toward the Sun.
        if elong <= COMBUST_ORB_DEG:
            return _phase("inferior", "combust_east_return", 8, "Combust (east, return)")
        if elong <= UNDER_BEAMS_ORB_DEG:
            return _phase("inferior", "under_beams_east_return", 7, "Under beams (east, return)")
        return _phase("inferior", "direct_east_closing", 6, "Direct east, closing to Sun")

    if is_occidental:
        if is_station:
            if planet.station == "second":
                return _phase("inferior", "second_station_west", 5, "Second station (west)")
            return _phase("inferior", "first_station_west", 13, "First station (west)")

        if is_direct:
            if elong <= COMBUST_ORB_DEG:
                return _phase("inferior", "combust_west", 10, "Combust (west)")
            if elong <= UNDER_BEAMS_ORB_DEG:
                return _phase("inferior", "under_beams_west", 11, "Under beams (west)")
            return _phase("inferior", "occidental_visible_direct", 12, "Direct west")

        if elong <= COMBUST_ORB_DEG:
            return _phase("inferior", "combust_west_return", 16, "Combust (west, return)")
        if elong <= UNDER_BEAMS_ORB_DEG:
            return _phase("inferior", "under_beams_west_return", 15, "Under beams (west, return)")
        return _phase(
            "inferior",
            "retrograde_west_towards_sun",
            14,
            "Retrograde west, returning to Sun",
        )

    return _phase("inferior", "cazimi", 1, "Cazimi")


def compute_lunar_synodic_phase(moon: PlanetPosition, sun_long: float) -> SynodicPhaseInfo:
    """Classify the Moon through the course's lunar synodic sequence.

    The project keeps its common 17'/7°30'/15° solar-contact thresholds, while
    the quarter/full-light transitions follow the course: 45°, 90°, 135° and
    12° from opposition (168° elongation).  The source jumps from phase 12 to
    phase 14 on the waning return; that historical numbering is preserved.
    """
    directed = (moon.longitude - sun_long) % 360.0
    elong = directed if directed <= 180.0 else 360.0 - directed

    if elong <= CAZIMI_ORB_DEG:
        return _phase("lunar", "cazimi", 1, "Cazimi")

    if abs(directed - 180.0) <= ANGLE_EPSILON:
        return _phase("lunar", "full", 9, "Full / opposition")

    waxing = directed < 180.0
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
        return _phase("lunar", "full_applying", 8, "Applying to full Moon")

    # Waning return after opposition.
    if elong >= 168.0:
        return _phase("lunar", "waning_near_full", 10, "Separating from full Moon")
    if elong >= 135.0:
        return _phase("lunar", "waning_gibbous", 11, "Waning gibbous")
    if elong >= 90.0:
        return _phase("lunar", "waning_quarter", 12, "Waning toward last quarter")
    if elong > UNDER_BEAMS_ORB_DEG:
        return _phase("lunar", "waning_crescent", 14, "Waning crescent")
    if elong > COMBUST_ORB_DEG:
        return _phase("lunar", "under_beams_west", 15, "Under beams (return)")
    return _phase("lunar", "combust_west", 16, "Combust (return)")
