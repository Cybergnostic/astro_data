from types import SimpleNamespace

from hor_tools.models import PlanetPosition, SynodicPhaseInfo
from hor_tools.output import _build_condition_lines, _build_motion_lines, _format_synodic
from hor_tools.synodic import CAZIMI_ORB_DEG, is_true_cazimi


def _planet(name: str, longitude: float, latitude: float) -> PlanetPosition:
    return PlanetPosition(
        name=name,
        longitude=longitude,
        latitude=latitude,
        speed_long=1.0,
        speed_lat=0.0,
        house=1,
        retrograde=False,
    )


def test_true_cazimi_working_rule_requires_longitude_and_latitude() -> None:
    sun = _planet("Sun", 100.0, 0.0)
    within_both = _planet("Mercury", 100.0 + CAZIMI_ORB_DEG, CAZIMI_ORB_DEG)
    outside_latitude = _planet("Mercury", 100.0 + CAZIMI_ORB_DEG / 2.0, CAZIMI_ORB_DEG + 0.0001)

    assert is_true_cazimi(within_both, sun)
    assert not is_true_cazimi(outside_latitude, sun)


def test_renderer_distinguishes_true_cazimi_and_accidental_conditions() -> None:
    phase = SynodicPhaseInfo(group="inferior", code="cazimi", index=1, label="Cazimi")
    planet = SimpleNamespace(
        retrograde=False,
        speed_long=1.0,
        latitude=0.20,
        synodic_phase=phase,
    )
    report = SimpleNamespace(
        planet=planet,
        is_cazimi=True,
        is_true_cazimi=True,
        speed_class="swift",
        speed_ratio=1.10,
        is_in_planetary_joy=True,
        latitude_condition="north_strengthening",
        is_in_via_combusta=True,
        is_void_of_course=True,
    )

    motion = "\n".join(_build_motion_lines(report, markup=False))
    conditions = "\n".join(_build_condition_lines(report, markup=False))
    synodic = _format_synodic(report, markup=False)

    assert "TRUE CAZIMI (lon+lat)" in motion
    assert "planetary joy" in conditions
    assert "north latitude: strengthening" in conditions
    assert "via combusta" in conditions
    assert "VOID OF COURSE" in conditions
    assert "TRUE CAZIMI" in synodic
