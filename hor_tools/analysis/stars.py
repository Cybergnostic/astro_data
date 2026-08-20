from __future__ import annotations

from typing import List

import swisseph as swe

from ..models import ChartInput
from ..astro_engine import julian_day_from_chart, ensure_ephe_path

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


def _star_orb_from_magnitude(magnitude: float) -> float:
    """Course working orbs: ~1°30' for first magnitude, 1° otherwise."""
    # Classical magnitude classes are centred on integer magnitudes; values
    # brighter than 1.5 belong to the first-magnitude class.
    return 1.5 if magnitude < 1.5 else 1.0


def stars_near_longitude(
    chart: ChartInput, body_longitude: float, max_orb: float | None = None
) -> List[str]:
    """
    Return selected bright stars conjunct a body in zodiacal longitude.

    Star positions are calculated for the chart epoch, so precession is handled
    dynamically. Unless an explicit override is supplied, the course's
    magnitude-sensitive working orb is used: about 1°30' for first-magnitude
    stars and 1° for second magnitude and weaker stars.
    """
    jd_ut = julian_day_from_chart(chart)
    ensure_ephe_path()

    hits: List[str] = []
    for name in BRIGHT_STARS:
        try:
            result = swe.fixstar_ut(name, jd_ut)
            magnitude = float(swe.fixstar_mag(name))
        except swe.Error:
            # Missing sefstars.txt or another fixed-star data problem.
            return []

        if not isinstance(result, (tuple, list)) or len(result) < 1:
            continue
        pos = result[0]
        if not isinstance(pos, (tuple, list)) or len(pos) < 1:
            continue

        lon = float(pos[0])
        diff = abs(body_longitude - lon) % 360.0
        diff = min(diff, 360.0 - diff)
        allowed_orb = max_orb if max_orb is not None else _star_orb_from_magnitude(magnitude)
        if diff <= allowed_orb:
            hits.append(name)

    return hits
