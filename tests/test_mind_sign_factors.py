from __future__ import annotations

from pathlib import Path

import pytest

from hor_tools import astro_engine
from hor_tools.analysis import build_reports
from hor_tools.analysis.natal_synthesis import (
    ASCENSION_BY_SIGN,
    MODALITY_BY_SIGN,
    PRIMARY_CONTACT_CORE_ORB,
    PRIMARY_CONTACT_ORB,
)
from hor_tools.analysis.technical import build_natal_technical_report
from hor_tools.hor_parser import load_hor


FIXTURE = Path(__file__).parent / "fixtures" / "sample_nis.hor"


def test_course_sign_modality_and_ascension_classes() -> None:
    assert MODALITY_BY_SIGN == {
        0: "cardinal",
        1: "fixed",
        2: "mutable",
        3: "cardinal",
        4: "fixed",
        5: "mutable",
        6: "cardinal",
        7: "fixed",
        8: "mutable",
        9: "cardinal",
        10: "fixed",
        11: "mutable",
    }
    assert [ASCENSION_BY_SIGN[index] for index in range(12)] == [
        "short-ascending",
        "short-ascending",
        "short-ascending",
        "long-ascending",
        "long-ascending",
        "long-ascending",
        "long-ascending",
        "long-ascending",
        "long-ascending",
        "short-ascending",
        "short-ascending",
        "short-ascending",
    ]


def test_primary_motivation_preserves_course_approximate_five_to_six_degree_limit() -> None:
    assert PRIMARY_CONTACT_CORE_ORB == 5.0
    assert PRIMARY_CONTACT_ORB == 6.0


def test_reference_chart_mind_records_sign_structure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(astro_engine, "EPHE_PATH", str(tmp_path))
    chart = load_hor(FIXTURE)
    planets = astro_engine.compute_planets(chart)
    houses = astro_engine.compute_houses(chart)
    reports, relationships = build_reports(chart, planets, houses)
    technical = build_natal_technical_report(
        chart, planets, houses, reports, relationships
    )

    mercury = technical.mind.mercury
    moon = technical.mind.moon
    assert "element: air — quick, curious, versatile and scattered" in mercury
    assert "modality: mutable" in mercury
    assert "ascension: short-ascending" in mercury
    assert "element: fire" in moon
    assert "modality: cardinal" in moon
    assert "ascension: short-ascending" in moon
