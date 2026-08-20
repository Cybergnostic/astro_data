from __future__ import annotations

from typing import List

import swisseph as swe

from ..models import ChartInput
from ..astro_engine import julian_day_from_chart, ensure_ephe_path

# Working catalogue from the course's fixed-star handout/table, plus named stars
# discussed individually in the same lesson. Each entry keeps a display name
# and one or more Swiss-Ephemeris lookup aliases; unresolved aliases are skipped
# individually rather than causing the entire fixed-star calculation to fail.
COURSE_STARS: list[tuple[str, tuple[str, ...]]] = [
    ("Deneb Kaitos", ("Deneb Kaitos", "Diphda")),
    ("Algenib", ("Algenib",)),
    ("Alpheratz", ("Alpheratz", "Alpherac")),
    ("Baten Kaitos", ("Baten Kaitos",)),
    ("Alpherg", ("Alpherg", "Al Pherg")),
    ("Vertex", ("Vertex",)),
    ("Mirach", ("Mirach",)),
    ("Mira", ("Mira",)),
    ("Sheratan", ("Sheratan",)),
    ("Hamal", ("Hamal",)),
    ("Schedar", ("Schedar", "Shedar")),
    ("Almach", ("Almach",)),
    ("Menkar", ("Menkar",)),
    ("Zaurak", ("Zaurak",)),
    ("Capulus", ("Capulus",)),
    ("Algol", ("Algol",)),
    ("Alcyone", ("Alcyone",)),
    ("Hyades", ("Hyades", "Prima Hyadum")),
    ("Ain", ("Ain",)),
    ("Aldebaran", ("Aldebaran",)),
    ("Rigel", ("Rigel",)),
    ("Bellatrix", ("Bellatrix",)),
    ("Capella", ("Capella",)),
    ("Mintaka", ("Mintaka",)),
    ("Elnath", ("Elnath", "El Nath")),
    ("Ensis", ("Ensis",)),
    ("Alnilam", ("Alnilam",)),
    ("Al Hecka", ("Al Hecka", "Alheka")),
    ("Polaris", ("Polaris",)),
    ("Betelgeuse", ("Betelgeuse",)),
    ("Menkalinan", ("Menkalinan",)),
    ("Propus", ("Propus",)),
    ("Tejat Posterior", ("Tejat Posterior", "Tejat")),
    ("Alhena", ("Alhena",)),
    ("Sirius", ("Sirius",)),
    ("Canopus", ("Canopus",)),
    ("Wasat", ("Wasat",)),
    ("Castor", ("Castor",)),
    ("Pollux", ("Pollux",)),
    ("Procyon", ("Procyon",)),
    ("Praesepe", ("Praesepe",)),
    ("Asellus Borealis", ("Asellus Borealis",)),
    ("Asellus Australis", ("Asellus Australis",)),
    ("Acubens", ("Acubens",)),
    ("Algenubi", ("Algenubi",)),
    ("Alphard", ("Alphard",)),
    ("Adhafera", ("Adhafera",)),
    ("Al Jabbah", ("Al Jabbah",)),
    ("Regulus", ("Regulus",)),
    ("Zosma", ("Zosma",)),
    ("Denebola", ("Denebola",)),
    ("Labrum", ("Labrum",)),
    ("Zavijava", ("Zavijava",)),
    ("Markeb", ("Markeb",)),
    ("Zaniah", ("Zaniah",)),
    ("Vindemiatrix", ("Vindemiatrix",)),
    ("Algorab", ("Algorab",)),
    ("Seginus", ("Seginus",)),
    ("Foramen", ("Foramen",)),
    ("Spica", ("Spica",)),
    ("Arcturus", ("Arcturus",)),
    ("Princeps", ("Princeps",)),
    ("Acrux", ("Acrux",)),
    ("Alphecca", ("Alphecca",)),
    ("Zuben Elgenubi", ("Zuben Elgenubi", "Zubenelgenubi")),
    ("Zuben Eschamali", ("Zuben Eschamali", "Zubeneschamali")),
    ("Unukalhai", ("Unukalhai",)),
    ("Agena", ("Agena", "Hadar")),
    ("Rigil Kentaurus", ("Rigil Kentaurus", "Toliman", "Bungula")),
    ("Yed Prior", ("Yed Prior",)),
    ("Isidis", ("Isidis",)),
    ("Acrab", ("Acrab", "Akrab")),
    ("Han", ("Han",)),
    ("Antares", ("Antares",)),
    ("Ras Algethi", ("Ras Algethi",)),
    ("Graffias", ("Graffias",)),
    ("Sabik", ("Sabik",)),
    ("Ras Alhague", ("Ras Alhague",)),
    ("Lesath", ("Lesath", "Lesat")),
    ("Aculeus", ("Aculeus",)),
    ("Acumen", ("Acumen",)),
    ("Sinistra", ("Sinistra",)),
    ("Spiculum", ("Spiculum",)),
    ("Polis", ("Polis",)),
    ("Facies", ("Facies", "Facis")),
    ("Nunki", ("Nunki", "Pelagus")),
    ("Ascella", ("Ascella", "Asella")),
    ("Manubrium", ("Manubrium",)),
    ("Vega", ("Vega",)),
    ("Deneb Okab", ("Deneb Okab",)),
    ("Terebellum", ("Terebellum",)),
    ("Albireo", ("Albireo",)),
    ("Altair", ("Altair",)),
    ("Giedi Prima", ("Giedi Prima",)),
    ("Giedi Secunda", ("Giedi Secunda",)),
    ("Dabih", ("Dabih",)),
    ("Oculus", ("Oculus",)),
    ("Bos", ("Bos",)),
    ("Armus", ("Armus",)),
    ("Dorsum", ("Dorsum",)),
    ("Castra", ("Castra",)),
    ("Nashira", ("Nashira",)),
    ("Sadalsuud", ("Sadalsuud",)),
    ("Deneb Algedi", ("Deneb Algedi",)),
    ("Sadalmelik", ("Sadalmelik", "Sadalmel(e)k")),
    ("Fomalhaut", ("Fomalhaut",)),
    ("Deneb Adige", ("Deneb Adige", "Deneb")),
    ("Skat", ("Skat",)),
    ("Achernar", ("Achernar",)),
    ("Markab", ("Markab",)),
    ("Scheat", ("Scheat",)),
    # Individually discussed in the handout even where not repeated in the
    # compact zodiacal-position table.
    ("Alioth", ("Alioth",)),
    ("Alkaid", ("Alkaid", "Benetnash")),
    ("Alnair", ("Alnair",)),
    ("Alnitak", ("Alnitak",)),
    ("Adara", ("Adara", "Adhara")),
    ("Alderamin", ("Alderamin",)),
]

# The handout explicitly marks these as first-magnitude stars. The value is the
# first (primary) planet in the handout's planetary-nature code. The temperament
# lecture says to use this first planet when a star has a double nature.
COURSE_FIRST_MAGNITUDE_PRIMARY_NATURE: dict[str, str] = {
    "Aldebaran": "Mars",
    "Rigel": "Jupiter",
    "Capella": "Mars",
    "Betelgeuse": "Mars",
    "Sirius": "Jupiter",
    "Canopus": "Saturn",
    "Pollux": "Mars",
    "Procyon": "Mercury",
    "Regulus": "Mars",
    "Spica": "Venus",
    "Arcturus": "Jupiter",
    "Acrux": "Jupiter",
    "Agena": "Venus",
    "Rigil Kentaurus": "Venus",
    "Antares": "Mars",
    "Vega": "Venus",
    "Altair": "Mars",
    "Fomalhaut": "Venus",
    "Deneb Adige": "Venus",
    "Achernar": "Jupiter",
}

# Backward-compatible public name for callers that imported the old constant.
BRIGHT_STARS = [display for display, _aliases in COURSE_STARS]


def _star_orb_from_magnitude(magnitude: float) -> float:
    """Course working orbs: ~1°30' first magnitude, ~1° weaker stars."""
    return 1.5 if magnitude < 1.5 else 1.0


def _resolve_star(
    aliases: tuple[str, ...], jd_ut: float
) -> tuple[tuple[float, ...], float] | None:
    for alias in aliases:
        try:
            result = swe.fixstar_ut(alias, jd_ut)
            magnitude_result = swe.fixstar_mag(alias)
            magnitude = float(magnitude_result[0])
        except (swe.Error, TypeError, ValueError, IndexError):
            continue

        if not isinstance(result, (tuple, list)) or not result:
            continue
        pos = result[0]
        if not isinstance(pos, (tuple, list)) or len(pos) < 2:
            continue
        return tuple(float(value) for value in pos), magnitude
    return None


def stars_near_longitude(
    chart: ChartInput,
    body_longitude: float,
    body_latitude: float | None = None,
    max_orb: float | None = None,
) -> List[str]:
    """Return course-catalogue fixed stars conjunct a body in longitude.

    Positions are queried for the chart epoch, so precession is dynamic. The
    teacher's working orb is magnitude-sensitive. Latitude is *not* used as a
    universal hard cutoff: the course treats real spatial/latitudinal nearness
    as a qualifier of how strongly a star contact manifests. When a body's
    latitude is supplied, the report therefore includes the absolute latitude
    separation for judgement.
    """
    jd_ut = julian_day_from_chart(chart)
    ensure_ephe_path()

    hits: List[str] = []
    for display_name, aliases in COURSE_STARS:
        resolved = _resolve_star(aliases, jd_ut)
        if resolved is None:
            continue
        pos, magnitude = resolved

        star_longitude = pos[0] % 360.0
        star_latitude = pos[1]
        diff = abs(body_longitude - star_longitude) % 360.0
        diff = min(diff, 360.0 - diff)
        allowed_orb = max_orb if max_orb is not None else _star_orb_from_magnitude(magnitude)
        if diff > allowed_orb:
            continue

        if body_latitude is None:
            hits.append(display_name)
        else:
            latitude_gap = abs(body_latitude - star_latitude)
            hits.append(f"{display_name} (Δlat {latitude_gap:.2f}°)")

    return hits
