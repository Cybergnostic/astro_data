from __future__ import annotations

from typing import Dict, Tuple

SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]

SIGN_RULERS = [
    "Mars",
    "Venus",
    "Mercury",
    "Moon",
    "Sun",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Saturn",
    "Jupiter",
]

EXALTATIONS = {
    0: "Sun",  # Aries
    1: "Moon",  # Taurus
    3: "Jupiter",  # Cancer
    5: "Mercury",  # Virgo
    6: "Saturn",  # Libra
    9: "Mars",  # Capricorn
    11: "Venus",  # Pisces
}

# Dorothean triplicity rulers: (day, night, participating)
TRIPLICITIES: Dict[str, Tuple[str, str, str]] = {
    "fire": ("Sun", "Jupiter", "Saturn"),
    "earth": ("Venus", "Moon", "Mars"),
    "air": ("Saturn", "Mercury", "Jupiter"),
    "water": ("Venus", "Mars", "Moon"),
}

# Egyptian terms (end degree within sign, planet)
TERMS: Dict[int, list[Tuple[float, str]]] = {
    0: [(6, "Jupiter"), (12, "Venus"), (20, "Mercury"), (25, "Mars"), (30, "Saturn")],  # Aries
    1: [(8, "Venus"), (14, "Mercury"), (22, "Jupiter"), (27, "Saturn"), (30, "Mars")],  # Taurus
    2: [(6, "Mercury"), (12, "Jupiter"), (17, "Venus"), (24, "Mars"), (30, "Saturn")],  # Gemini
    3: [(7, "Mars"), (13, "Venus"), (19, "Mercury"), (26, "Jupiter"), (30, "Saturn")],  # Cancer
    4: [(6, "Jupiter"), (11, "Venus"), (18, "Saturn"), (24, "Mercury"), (30, "Mars")],  # Leo
    5: [(7, "Mercury"), (17, "Venus"), (21, "Jupiter"), (28, "Mars"), (30, "Saturn")],  # Virgo
    6: [(6, "Saturn"), (14, "Mercury"), (21, "Jupiter"), (28, "Venus"), (30, "Mars")],  # Libra
    7: [(7, "Mars"), (11, "Venus"), (19, "Mercury"), (24, "Jupiter"), (30, "Saturn")],  # Scorpio
    8: [(12, "Jupiter"), (17, "Venus"), (21, "Mercury"), (26, "Saturn"), (30, "Mars")],  # Sagittarius
    9: [(7, "Mercury"), (14, "Jupiter"), (22, "Venus"), (26, "Saturn"), (30, "Mars")],  # Capricorn
    10: [(7, "Mercury"), (13, "Venus"), (20, "Jupiter"), (25, "Mars"), (30, "Saturn")],  # Aquarius
    11: [(12, "Venus"), (16, "Jupiter"), (19, "Mercury"), (28, "Mars"), (30, "Saturn")],  # Pisces
}

CHALDEAN_SEQUENCE = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]

MEAN_SPEED: Dict[str, float] = {
    "Sun": 0.9856,
    "Moon": 13.1764,
    "Mercury": 1.607,
    "Venus": 1.174,
    "Mars": 0.524,
    "Jupiter": 0.0831,
    "Saturn": 0.0335,
}


def sign_index_from_longitude(longitude: float) -> int:
    return int(longitude // 30) % 12


def degree_in_sign(longitude: float) -> float:
    return longitude % 30.0


def essential_dignity(planet_name: str, longitude: float, is_day_chart: bool) -> dict:
    """
    Returns a dict with keys:
    sign, ruler, exaltation_lord, triplicity_lord, term_lord, face_lord,
    is_domicile, is_exalted, is_detriment, is_fall
    """

    sign_idx = sign_index_from_longitude(longitude)
    sign_name = SIGNS[sign_idx]
    ruler = SIGN_RULERS[sign_idx]
    exaltation_lord = EXALTATIONS.get(sign_idx)

    triplicity_lord = _triplicity_for_sign(sign_idx, is_day_chart)
    term_lord = _term_lord(sign_idx, degree_in_sign(longitude))
    face_lord = _face_lord(sign_idx, degree_in_sign(longitude))

    domicile = planet_name == ruler
    detriment = planet_name == SIGN_RULERS[(sign_idx + 6) % 12]
    exalted = planet_name == exaltation_lord
    fall = planet_name == EXALTATIONS.get((sign_idx + 6) % 12)

    return {
        "sign": sign_name,
        "ruler": ruler,
        "exaltation_lord": exaltation_lord,
        "triplicity_lord": triplicity_lord,
        "term_lord": term_lord,
        "face_lord": face_lord,
        "is_domicile": domicile,
        "is_exalted": exalted,
        "is_detriment": detriment,
        "is_fall": fall,
    }


def classify_speed(planet_name: str, speed_long: float) -> tuple[float, str]:
    """
    Returns (ratio, class) where class is:
    - "slow" if ratio < 0.8
    - "swift" if ratio > 1.2
    - "average" otherwise
    """

    mean = MEAN_SPEED.get(planet_name)
    if not mean or mean == 0:
        return 0.0, "average"
    ratio = abs(speed_long) / mean
    if ratio < 0.8:
        cls = "slow"
    elif ratio > 1.2:
        cls = "swift"
    else:
        cls = "average"
    return ratio, cls


def _triplicity_for_sign(sign_idx: int, is_day_chart: bool) -> str:
    element = _element_for_sign(sign_idx)
    day, night, participating = TRIPLICITIES[element]
    if is_day_chart:
        return day
    return night or participating


def _element_for_sign(sign_idx: int) -> str:
    if sign_idx in {0, 4, 8}:
        return "fire"
    if sign_idx in {1, 5, 9}:
        return "earth"
    if sign_idx in {2, 6, 10}:
        return "air"
    return "water"


def _term_lord(sign_idx: int, degree: float) -> str | None:
    for end_degree, lord in TERMS.get(sign_idx, []):
        if degree <= end_degree:
            return lord
    return None


def _face_lord(sign_idx: int, degree: float) -> str:
    decan = int(degree // 10)
    decan_index = sign_idx * 3 + decan
    start_offset = 2  # Mars is the first decan ruler of Aries
    return CHALDEAN_SEQUENCE[(start_offset + decan_index) % len(CHALDEAN_SEQUENCE)]


def dignity_holders_for_position(longitude: float, is_day_chart: bool) -> dict[str, str | None]:
    """Return the planets holding each essential dignity at a longitude."""

    sign_idx = sign_index_from_longitude(longitude)
    deg = degree_in_sign(longitude)
    ruler = SIGN_RULERS[sign_idx]
    exaltation_lord = EXALTATIONS.get(sign_idx)
    triplicity_lord = _triplicity_for_sign(sign_idx, is_day_chart)
    term_lord = _term_lord(sign_idx, deg)
    face_lord = _face_lord(sign_idx, deg)
    return {
        "domicile": ruler,
        "exaltation": exaltation_lord,
        "triplicity": triplicity_lord,
        "term": term_lord,
        "face": face_lord,
    }
