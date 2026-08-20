from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from hor_tools.cli import _scan_helper_template, build_parser, resolve_output_path
from hor_tools.commands.asc_window import scan_asc_changes
from hor_tools.commands.scan_events import scan_range
from hor_tools.models import ChartInput


def _chart() -> ChartInput:
    return ChartInput(
        name="test",
        datetime_utc=datetime(2026, 8, 20, 10, 0, tzinfo=timezone.utc),
        tz_offset_hours=2.0,
        latitude=43.32,
        longitude=21.9,
        house_system="W",
        zodiac="T",
    )


def test_main_cli_rejects_unknown_options() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--not-a-real-option", "chart.hor"])
    assert exc.value.code == 2


def test_main_cli_requires_exactly_one_input_file() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["one.hor", "two.hor"])
    assert exc.value.code == 2


def test_scan_template_uses_installed_command() -> None:
    command = _scan_helper_template(_chart(), "/tmp/ephe")
    assert command.startswith("hor-scan-events ")
    assert ' --ephe "/tmp/ephe"' in command


def test_simple_output_name_goes_under_outputs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    resolved = resolve_output_path("report.md")
    assert resolved == Path("outputs/report.md")
    assert (tmp_path / "outputs").is_dir()


def test_event_scanner_rejects_nonpositive_step_before_looping() -> None:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = datetime(2026, 1, 2, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="step-min"):
        scan_range(start, end, 0.0, 0.0, 0.0, 0.1, {})


def test_asc_scanner_rejects_nonpositive_step_before_looping() -> None:
    chart = _chart()
    with pytest.raises(ValueError, match="step-min"):
        scan_asc_changes(
            chart,
            date_start := chart.datetime_utc.date(),
            date_start,
            datetime.min.time(),
            datetime.max.time(),
            0.0,
            0.1,
        )
