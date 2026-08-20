from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from hor_tools.hor_parser import HorParseError, load_hor


FIXTURE = Path(__file__).parent / "fixtures" / "sample_nis.hor"


def test_real_morinus_header_is_parsed_exactly() -> None:
    chart = load_hor(FIXTURE)

    assert chart.name == "Sample"
    assert chart.location_name == "Niš"
    assert chart.altitude_m == 195.0
    assert chart.datetime_utc == datetime(1988, 6, 8, 17, 15, tzinfo=timezone.utc)
    assert chart.tz_offset_hours == 2.0
    assert chart.longitude == pytest.approx(21.9)
    assert chart.latitude == pytest.approx(43 + 19 / 60)


def test_incomplete_file_fails_instead_of_guessing(tmp_path: Path) -> None:
    path = tmp_path / "broken.hor"
    path.write_text("VBroken\n.I1988\n.I6\n.I8\n", encoding="ascii")

    with pytest.raises(HorParseError, match="header is incomplete"):
        load_hor(path)


def test_invalid_coordinate_fails_instead_of_falling_back_to_zero(tmp_path: Path) -> None:
    text = FIXTURE.read_text(encoding="ascii").replace(".I43\n.I19", ".I143\n.I19")
    path = tmp_path / "bad_latitude.hor"
    path.write_text(text, encoding="ascii")

    with pytest.raises(HorParseError, match="latitude degrees"):
        load_hor(path)


def test_western_zone_and_southern_western_coordinates_are_signed(tmp_path: Path) -> None:
    lines = FIXTURE.read_text(encoding="ascii").splitlines()
    int_line_indexes = [i for i, line in enumerate(lines) if line.startswith(".I")]

    # Morinus header integer indexes: plus=11, east=18, north=22.
    lines[int_line_indexes[11]] = ".I0"
    lines[int_line_indexes[18]] = ".I0"
    lines[int_line_indexes[22]] = ".I0"

    path = tmp_path / "west_south.hor"
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    chart = load_hor(path)

    # UTC-1 base zone + DST => effective UTC+0 for this synthetic fixture.
    assert chart.tz_offset_hours == 0.0
    assert chart.datetime_utc == datetime(1988, 6, 8, 19, 15, tzinfo=timezone.utc)
    assert chart.longitude == pytest.approx(-21.9)
    assert chart.latitude == pytest.approx(-(43 + 19 / 60))


def test_unsupported_local_apparent_time_is_explicit(tmp_path: Path) -> None:
    lines = FIXTURE.read_text(encoding="ascii").splitlines()
    int_line_indexes = [i for i, line in enumerate(lines) if line.startswith(".I")]
    lines[int_line_indexes[10]] = ".I3"

    path = tmp_path / "lat_time.hor"
    path.write_text("\n".join(lines) + "\n", encoding="ascii")

    with pytest.raises(HorParseError, match="Local-apparent-time"):
        load_hor(path)
