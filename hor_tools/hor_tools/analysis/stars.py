from __future__ import annotations

from typing import List

import swisseph as swe

from ..models import ChartInput
from ..astro_engine import julian_day_from_chart, EPHE_PATH

BRIGHT_STARS = [
    "Regulus",
    "Spica",
    "Aldebaran",
    "Antares",
    "Fomalhaut",
    "Sirius",
    "Vega",
    "Capella",
    "Altair",
    "Castor",
    "Pollux",
]


def stars_near_longitude(
    chart: ChartInput, body_longitude: float, max_orb: float = 3.0
) -> List[str]:
    """
    Return list of bright star names within max_orb degrees in longitude.

    On this system swe.fixstar_ut returns:
        ((lon, lat, dist, 0, 0, 0), "Name,abbrev", flag)

    If fixed-star data is not available, return an empty list instead of raising.
    """
    jd_ut = julian_day_from_chart(chart)

    # Use the same ephemeris path as planets.
    swe.set_ephe_path(EPHE_PATH)

    hits: List[str] = []

    for name in BRIGHT_STARS:
        try:
            result = swe.fixstar_ut(name, jd_ut)
        except swe.Error:
            # Missing sefstars.txt or some other fixed-star problem.
            return []

        # Expect: (position_tuple, star_name_str, flags_int)
        if not isinstance(result, (tuple, list)) or len(result) < 1:
            continue

        pos = result[0]
        if not isinstance(pos, (tuple, list)) or len(pos) < 1:
            continue

        lon = float(pos[0])

        # Distance in zodiacal longitude
        diff = abs(body_longitude - lon)
        diff = min(diff, 360.0 - diff)

        if diff <= max_orb:
            hits.append(name)

    return hits
