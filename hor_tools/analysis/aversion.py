"""Aversion to own domicile(s) and avoidance rules."""

from __future__ import annotations

from typing import List

from .antiscia import antiscia_longitude, contra_antiscia_longitude
from .dignity import SIGN_RULERS, SIGNS, sign_index_from_longitude
from ..models import DomicileAversion, PlanetPosition, PlanetReport, TranslationOfLight


def domiciles_for_planet(planet_name: str) -> list[int]:
    """Return sign indices ruled by planet_name."""
    return [idx for idx, ruler in enumerate(SIGN_RULERS) if ruler == planet_name]


def _signs_in_aspect(a_idx: int, b_idx: int) -> bool:
    """Whole-sign aspect check: conjunction, sextile, square, trine, opposition."""
    dist = (b_idx - a_idx) % 12
    return dist in {0, 2, 3, 4, 6}


def _antiscia_pair(sign_idx: int) -> int:
    """Return the sign index that is antiscia to sign_idx (sign-level)."""
    center_long = sign_idx * 30.0 + 15.0
    return sign_index_from_longitude(antiscia_longitude(center_long))


def _contra_antiscia_pair(sign_idx: int) -> int:
    """Return the sign index that is contra-antiscia to sign_idx (sign-level)."""
    center_long = sign_idx * 30.0 + 15.0
    return sign_index_from_longitude(contra_antiscia_longitude(center_long))


def compute_domicile_aversion(
    reports: List[PlanetReport],
    planets: List[PlanetPosition],
    translations: List[TranslationOfLight],
) -> None:
    """
    For each planet, mark whether it sees each of its domiciles or is in aversion.

    Aversion is avoided if:
      1) A translation of light links the planet with a planet located in its domicile sign, or
      2) The planet is in a sign that is antiscia or contra-antiscia to its domicile sign.
    """
    sign_map = {p.name: sign_index_from_longitude(p.longitude) for p in planets}
    occupants_by_sign: dict[int, list[str]] = {}
    for p in planets:
        occupants_by_sign.setdefault(sign_map[p.name], []).append(p.name)

    for rep in reports:
        name = rep.planet.name
        current_sign = sign_map[name]
        doms = domiciles_for_planet(name)
        aversions: list[DomicileAversion] = []
        for dom_idx in doms:
            sees = _signs_in_aspect(current_sign, dom_idx)
            avoided = False
            avoided_by: list[str] = []
            occupants = occupants_by_sign.get(dom_idx, [])

            if not sees:
                # Rule 1: translation of light via a planet in domicile sign.
                for t in translations:
                    if name not in {t.from_planet, t.to_planet}:
                        continue
                    other = t.to_planet if t.from_planet == name else t.from_planet
                    if sign_map.get(other) == dom_idx:
                        avoided = True
                        avoided_by.append(f"translation via {t.translator} with {other}")
                # Rule 2: antiscia / contra-antiscia sign pairing
                if not avoided:
                    anti_pair = _antiscia_pair(dom_idx)
                    contra_pair = _contra_antiscia_pair(dom_idx)
                    if current_sign == anti_pair:
                        avoided = True
                        avoided_by.append("antiscia sign pairing")
                    elif current_sign == contra_pair:
                        avoided = True
                        avoided_by.append("contra-antiscia sign pairing")

            aversions.append(
                DomicileAversion(
                    domicile_sign=SIGNS[dom_idx],
                    sees=sees,
                    avoided=avoided,
                    avoided_by=avoided_by,
                    occupants=occupants,
                )
            )

        rep.domicile_aversions = aversions
