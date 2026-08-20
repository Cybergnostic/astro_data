from hor_tools.almuten import EssentialRow
from hor_tools.almuten_types import AccidentalScores, AlmutenResult


def test_typed_almuten_results_keep_mapping_compatibility() -> None:
    row = EssentialRow(
        name="Asc",
        longitude=248.0,
        contributions={"Mercury": [3]},
        totals={"Mercury": 3},
        winners=["Mercury"],
    )
    accidental = AccidentalScores(
        house_scores={"Mercury": 10},
        day_ruler="Mercury",
        hour_ruler="Mars",
        day_bonus={"Mercury": 7},
        hour_bonus={"Mars": 6},
        phase_scores={"Mars": 2},
        accidental_totals={"Mercury": 17, "Mars": 17},
    )
    result = AlmutenResult(
        rows=[row],
        total_shares={"Mercury": 1},
        essential_totals={"Mercury": 27},
        accidental=accidental,
        grand_scores={"Mercury": 44},
        almuten=["Mercury"],
        almuten_score=44,
    )

    assert result.almuten == ["Mercury"]
    assert result["grand_scores"] == {"Mercury": 44}
    assert result["accidental"] is accidental
    assert accidental.day_ruler == "Mercury"
    assert accidental["phase_scores"] == {"Mars": 2}
