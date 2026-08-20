from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from hor_tools import astro_engine


def test_ephemeris_path_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(astro_engine, "EPHE_PATH", None)
    monkeypatch.delenv("SWISSEPH_EPHE", raising=False)

    with pytest.raises(RuntimeError, match="path is not set"):
        astro_engine.ensure_ephe_path()


def test_ephemeris_path_must_be_a_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    missing = tmp_path / "missing"
    monkeypatch.setattr(astro_engine, "EPHE_PATH", str(missing))

    with pytest.raises(RuntimeError, match="does not exist"):
        astro_engine.ensure_ephe_path()


def test_valid_ephemeris_path_is_resolved_and_activated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(astro_engine, "EPHE_PATH", str(tmp_path))

    with patch("hor_tools.astro_engine.swe.set_ephe_path") as set_path:
        resolved = astro_engine.ensure_ephe_path()

    assert resolved == str(tmp_path.resolve())
    set_path.assert_called_once_with(str(tmp_path.resolve()))


def test_lightweight_longitude_api_does_not_request_speed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(astro_engine, "EPHE_PATH", str(tmp_path))
    fake_result = ((123.5, 0.0, 1.0, 0.0, 0.0, 0.0), 0)

    with patch("hor_tools.astro_engine.swe.set_ephe_path"), patch(
        "hor_tools.astro_engine.swe.calc_ut", return_value=fake_result
    ) as calc_ut:
        longitude = astro_engine._planet_longitude(2451545.0, 0)

    assert longitude == pytest.approx(123.5)
    calc_ut.assert_called_once_with(2451545.0, 0, astro_engine.LONGITUDE_FLAGS)
    assert not (astro_engine.LONGITUDE_FLAGS & astro_engine.swe.FLG_SPEED)
