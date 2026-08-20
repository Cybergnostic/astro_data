"""Backward-compatible imports for the consolidated relationship engine.

The corrected implementations now live in ``relationships.py``. This module is
kept only so older imports do not silently call a second, divergent rule set.
"""

from .relationships import (  # noqa: F401
    _qualifies_for_reception,
    aggregate_relationships,
    compute_collection_of_light,
    compute_domination,
    compute_receptions_and_generosity,
)

__all__ = [
    "_qualifies_for_reception",
    "aggregate_relationships",
    "compute_collection_of_light",
    "compute_domination",
    "compute_receptions_and_generosity",
]
