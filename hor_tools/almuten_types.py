"""Typed result objects for Almuten Figuris calculations."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .almuten import EssentialRow


@dataclass(frozen=True)
class AccidentalScores(Mapping[str, object]):
    """Accidental Almuten components for all traditional planets."""

    house_scores: dict[str, int]
    day_ruler: str
    hour_ruler: str
    day_bonus: dict[str, int]
    hour_bonus: dict[str, int]
    phase_scores: dict[str, int]
    accidental_totals: dict[str, int]

    _FIELDS = (
        "house_scores",
        "day_ruler",
        "hour_ruler",
        "day_bonus",
        "hour_bonus",
        "phase_scores",
        "accidental_totals",
    )

    def __getitem__(self, key: str) -> object:
        if key not in self._FIELDS:
            raise KeyError(key)
        return getattr(self, key)

    def __iter__(self) -> Iterator[str]:
        return iter(self._FIELDS)

    def __len__(self) -> int:
        return len(self._FIELDS)


@dataclass(frozen=True)
class AlmutenResult(Mapping[str, object]):
    """Complete Almuten Figuris result with typed, named components.

    Mapping compatibility is intentional: older renderers and callers that use
    ``result[\"grand_scores\"]`` continue to work while new code can use normal
    attributes such as ``result.grand_scores``.
    """

    rows: list[EssentialRow]
    total_shares: dict[str, int]
    essential_totals: dict[str, int]
    accidental: AccidentalScores
    grand_scores: dict[str, int]
    almuten: list[str]
    almuten_score: int

    _FIELDS = (
        "rows",
        "total_shares",
        "essential_totals",
        "accidental",
        "grand_scores",
        "almuten",
        "almuten_score",
    )

    def __getitem__(self, key: str) -> object:
        if key not in self._FIELDS:
            raise KeyError(key)
        return getattr(self, key)

    def __iter__(self) -> Iterator[str]:
        return iter(self._FIELDS)

    def __len__(self) -> int:
        return len(self._FIELDS)
