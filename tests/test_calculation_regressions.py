from __future__ import annotations

from datetime import datetime, timezone
import unittest

import swisseph as swe

from asc_window_scan import offset_hours_at, resolve_zone
from hor_tools.analysis.aspects import PLANET_ORBS, _is_applying
from hor_tools.analysis.conditions import (
    _crosses_major_aspect,
    is_in_planetary_joy,
    is_in_via_combusta,
    latitude_condition,
)
from hor_tools.analysis.dignity import MEAN_SPEED, _term_lord, classify_speed
from hor_tools.analysis.relationship_rules import (
    _qualifies_for_reception,
    compute_collection_of_light,
    compute_domination,
)
from hor_tools.analysis.sect import chart_sect, compute_hayz_and_halb
from hor_tools.analysis.stars import _star_orb_from_magnitude
from hor_tools.astro_engine import julian_day_from_chart
from hor_tools.models import AspectInfo, ChartInput, PlanetPosition
from scan_events import _crossed_aspect_target


def _planet(
    name: str,
    longitude: float,
    speed: float,
    house: int = 1,
    latitude: float = 0.0,
) -> PlanetPosition:
    return PlanetPosition(
        name=name,
        longitude=longitude,
        latitude=latitude,
        speed_long=speed,
        speed_lat=0.0,
        house=house,
        retrograde=speed < 0,
    )


class DignityRegressionTest(unittest.TestCase):
    def test_exact_term_boundary_belongs_to_next_term(self) -> None:
        self.assertEqual("Jupiter", _term_lord(0, 5.999999))
        self.assertEqual("Venus", _term_lord(0, 6.0))
        self.assertEqual("Mercury", _term_lord(0, 12.0))

    def test_speed_is_compared_directly_with_mean(self) -> None:
        mean = MEAN_SPEED["Mars"]
        self.assertEqual("slow", classify_speed("Mars", mean * 0.99)[1])
        self.assertEqual("average", classify_speed("Mars", mean)[1])
        self.assertEqual("swift", classify_speed("Mars", mean * 1.01)[1])

    def test_private_teacher_orbs_are_preserved(self) -> None:
        self.assertEqual(
            {
                "Saturn": 9.0,
                "Jupiter": 10.0,
                "Mars": 7.0,
                "Sun": 15.0,
                "Venus": 7.5,
                "Mercury": 7.0,
                "Moon": 12.0,
            },
            PLANET_ORBS,
        )


class AspectGeometryRegressionTest(unittest.TestCase):
    def test_applying_conjunction_across_zero_aries(self) -> None:
        moving = _planet("Mercury", 359.0, 1.0)
        other = _planet("Saturn", 1.0, 0.0)
        self.assertTrue(_is_applying(moving, other, 0.0))

    def test_separating_conjunction_across_zero_aries(self) -> None:
        moving = _planet("Mercury", 1.0, 1.0)
        other = _planet("Saturn", 359.0, 0.0)
        self.assertFalse(_is_applying(moving, other, 0.0))

    def test_negative_branch_of_sextile_is_handled(self) -> None:
        moving = _planet("Mercury", 1.0, -1.0)
        other = _planet("Saturn", 300.0, 0.0)
        self.assertTrue(_is_applying(moving, other, 60.0))


class RelationshipRuleRegressionTest(unittest.TestCase):
    def test_reception_thresholds(self) -> None:
        self.assertTrue(_qualifies_for_reception(["domicile"]))
        self.assertTrue(_qualifies_for_reception(["exaltation"]))
        self.assertTrue(_qualifies_for_reception(["triplicity", "term"]))
        self.assertTrue(_qualifies_for_reception(["triplicity", "face"]))
        self.assertTrue(_qualifies_for_reception(["term", "face"]))
        self.assertFalse(_qualifies_for_reception(["triplicity"]))
        self.assertFalse(_qualifies_for_reception(["term"]))
        self.assertFalse(_qualifies_for_reception(["face"]))

    def test_collector_need_not_be_globally_slowest(self) -> None:
        mercury = _planet("Mercury", 60.0, 1.0)
        venus = _planet("Venus", 300.0, 0.8)
        jupiter = _planet("Jupiter", 0.0, 0.1)
        saturn = _planet("Saturn", 180.0, 0.01)
        applying = AspectInfo(
            other="Jupiter",
            kind="sextile",
            orb=1.0,
            applying=True,
            dexter=False,
            self_applying=True,
        )
        lookup = {
            ("Mercury", "Jupiter"): applying,
            ("Venus", "Jupiter"): applying,
        }
        collections = compute_collection_of_light(
            [mercury, venus, jupiter, saturn], lookup
        )
        self.assertTrue(any(c.collector == "Jupiter" for c in collections))

    def test_aktinobolia_requires_application(self) -> None:
        dominated = _planet("Sun", 0.0, 1.0)
        dominator = _planet("Saturn", 270.0, 0.03)
        separating = AspectInfo(
            other="Sun",
            kind="square",
            orb=2.0,
            applying=False,
            dexter=True,
            self_applying=False,
        )
        doms = compute_domination(
            [dominated, dominator], {("Saturn", "Sun"): separating}
        )
        self.assertFalse(next(d for d in doms if d.dominator == "Saturn").has_counter_ray)

        applying = AspectInfo(
            other="Sun",
            kind="square",
            orb=2.0,
            applying=True,
            dexter=True,
            self_applying=True,
        )
        doms = compute_domination(
            [dominated, dominator], {("Saturn", "Sun"): applying}
        )
        self.assertTrue(next(d for d in doms if d.dominator == "Saturn").has_counter_ray)


class AccidentalConditionRegressionTest(unittest.TestCase):
    def test_planetary_joy_table(self) -> None:
        self.assertTrue(is_in_planetary_joy(_planet("Mercury", 0.0, 1.0, house=1)))
        self.assertTrue(is_in_planetary_joy(_planet("Moon", 0.0, 13.0, house=3)))
        self.assertTrue(is_in_planetary_joy(_planet("Venus", 0.0, 1.0, house=5)))
        self.assertTrue(is_in_planetary_joy(_planet("Mars", 0.0, 0.5, house=6)))
        self.assertTrue(is_in_planetary_joy(_planet("Sun", 0.0, 1.0, house=9)))
        self.assertTrue(is_in_planetary_joy(_planet("Jupiter", 0.0, 0.08, house=11)))
        self.assertTrue(is_in_planetary_joy(_planet("Saturn", 0.0, 0.03, house=12)))
        self.assertFalse(is_in_planetary_joy(_planet("Saturn", 0.0, 0.03, house=11)))

    def test_latitude_strength_testimony(self) -> None:
        self.assertEqual("north_strengthening", latitude_condition(_planet("Venus", 0.0, 1.0, latitude=2.0)))
        self.assertEqual("south_weakening", latitude_condition(_planet("Venus", 0.0, 1.0, latitude=-2.0)))
        self.assertEqual("on_ecliptic", latitude_condition(_planet("Venus", 0.0, 1.0, latitude=0.0)))

    def test_via_combusta_formal_course_core(self) -> None:
        self.assertFalse(is_in_via_combusta(198.9999))
        self.assertTrue(is_in_via_combusta(199.0))  # 19° Libra
        self.assertTrue(is_in_via_combusta(212.9999))
        self.assertTrue(is_in_via_combusta(213.0))  # 3° Scorpio
        self.assertFalse(is_in_via_combusta(213.0001))

    def test_void_of_course_aspect_crossing_uses_both_branches(self) -> None:
        self.assertTrue(_crosses_major_aspect(299.5, 300.5))
        self.assertTrue(_crosses_major_aspect(359.5, 0.5))
        self.assertFalse(_crosses_major_aspect(301.0, 302.0))


class HorizonRegressionTest(unittest.TestCase):
    def test_sect_uses_true_horizon_not_whole_sign_house(self) -> None:
        chart = ChartInput(
            name="horizon",
            datetime_utc=datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc),
            tz_offset_hours=0.0,
            latitude=43.32,
            longitude=21.90,
            house_system="W",
            zodiac="T",
        )
        jd = julian_day_from_chart(chart)
        _cusps, ascmc = swe.houses_ex(jd, chart.latitude, chart.longitude, b"P")
        mc = float(ascmc[1])

        above = _planet("Sun", mc, 1.0, house=1)
        below = _planet("Sun", (mc + 180.0) % 360.0, 1.0, house=10)
        self.assertEqual("day", chart_sect(chart, above))
        self.assertEqual("night", chart_sect(chart, below))

    def test_halb_uses_true_horizon(self) -> None:
        chart = ChartInput(
            name="halb",
            datetime_utc=datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc),
            tz_offset_hours=0.0,
            latitude=43.32,
            longitude=21.90,
            house_system="W",
            zodiac="T",
        )
        jd = julian_day_from_chart(chart)
        _cusps, ascmc = swe.houses_ex(jd, chart.latitude, chart.longitude, b"P")
        mc = float(ascmc[1])
        jupiter = _planet("Jupiter", mc, 0.08, house=1)
        _hayz, halb = compute_hayz_and_halb(jupiter, chart, "day", "day")
        self.assertTrue(halb)


class FixedStarRegressionTest(unittest.TestCase):
    def test_magnitude_sensitive_orbs(self) -> None:
        self.assertEqual(1.5, _star_orb_from_magnitude(0.9))
        self.assertEqual(1.5, _star_orb_from_magnitude(1.49))
        self.assertEqual(1.0, _star_orb_from_magnitude(1.5))
        self.assertEqual(1.0, _star_orb_from_magnitude(2.3))


class EventScannerRegressionTest(unittest.TestCase):
    def test_both_aspect_branches_and_wrap_are_detected(self) -> None:
        self.assertAlmostEqual(300.0, _crossed_aspect_target(299.0, 301.0, 60.0))
        self.assertIsNotNone(_crossed_aspect_target(359.0, 1.0, 0.0))
        self.assertAlmostEqual(180.0, _crossed_aspect_target(179.0, 181.0, 180.0))


class DstRegressionTest(unittest.TestCase):
    def test_iana_zone_changes_offset_across_dst(self) -> None:
        template = ChartInput(
            name="dst",
            datetime_utc=datetime(2026, 1, 1, tzinfo=timezone.utc),
            tz_offset_hours=1.0,
            latitude=43.32,
            longitude=21.90,
            house_system="W",
            zodiac="T",
        )
        zone = resolve_zone(template, "Europe/Belgrade")
        winter = datetime(2026, 1, 15, 12, tzinfo=timezone.utc)
        summer = datetime(2026, 7, 15, 12, tzinfo=timezone.utc)
        self.assertEqual(1.0, offset_hours_at(winter, zone))
        self.assertEqual(2.0, offset_hours_at(summer, zone))


if __name__ == "__main__":
    unittest.main()
