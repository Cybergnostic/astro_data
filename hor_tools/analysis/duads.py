"""Dodekatemoria (duads) used by the course."""

from __future__ import annotations

from dataclasses import dataclass

from .dignity import SIGNS, sign_index_from_longitude


@dataclass(frozen=True)
class DuadPosition:
    source_longitude: float
    longitude: float
    sign: str
    degree_in_sign: float


def dodekatemorion_longitude(longitude: float) -> float:
    """Return the zodiacal dodekatemorion longitude.

    Each 30° sign is projected through a complete 360° cycle: multiply the
    degree-within-sign by twelve and count that arc from the beginning of the
    natal sign.  This reproduces the course examples (9°24' Libra -> 22°48'
    Capricorn; 20°17' Scorpio -> 3°24' Cancer).
    """

    source_sign = sign_index_from_longitude(longitude)
    degree = longitude % 30.0
    return (source_sign * 30.0 + degree * 12.0) % 360.0


def dodekatemorion(longitude: float) -> DuadPosition:
    result = dodekatemorion_longitude(longitude)
    sign_idx = sign_index_from_longitude(result)
    return DuadPosition(
        source_longitude=longitude % 360.0,
        longitude=result,
        sign=SIGNS[sign_idx],
        degree_in_sign=result % 30.0,
    )
