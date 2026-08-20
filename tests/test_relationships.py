import datetime
import unittest
from unittest.mock import patch

from hor_tools.analysis import build_reports
from hor_tools.models import ChartInput, Houses, PlanetPosition


def _make_pos(name: str, lon: float, speed: float, house: int = 1) -> PlanetPosition:
    return PlanetPosition(
        name=name,
        longitude=lon,
        latitude=0.0,
        speed_long=speed,
        speed_lat=0.0,
        house=house,
        retrograde=speed < 0,
    )


def _dummy_chart() -> ChartInput:
    return ChartInput(
        name="synthetic",
        datetime_utc=datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc),
        tz_offset_hours=0.0,
        latitude=0.0,
        longitude=0.0,
        house_system="W",
        zodiac="T",
    )


def _dummy_houses() -> Houses:
    cusps = [0.0] + [i * 30.0 for i in range(12)]
    return Houses(cusps=cusps, asc=0.0, mc=90.0)


@patch("hor_tools.analysis.stars_near_longitude", new=lambda *args, **kwargs: [])
@patch("hor_tools.analysis.moon_void_of_course", new=lambda *args, **kwargs: False)
class RelationshipDetectionTest(unittest.TestCase):
    def test_primary_relationships(self) -> None:
        planets = [
            _make_pos("Sun", 0.0, 1.0, house=10),
            _make_pos("Venus", 10.0, 0.6),
            _make_pos("Mercury", 48.0, 1.0),
            _make_pos("Jupiter", 70.0, 0.2),
            _make_pos("Mars", 109.0, -0.3),
            _make_pos("Saturn", 270.0, 0.02),
            _make_pos("Moon", 210.0, 13.0),
        ]
        reports, relationships = build_reports(_dummy_chart(), planets, _dummy_houses())

        merc = next(r for r in reports if r.planet.name == "Mercury")
        mars_aspect = next(a for a in merc.aspects if a.other == "Mars")
        self.assertTrue(mars_aspect.mutual_application)

        moon = next(r for r in reports if r.planet.name == "Moon")
        saturn_aspect = next(a for a in moon.aspects if a.other == "Saturn")
        self.assertTrue(saturn_aspect.mutual_separation)

        dom = next(d for d in relationships.dominations if d.dominated == "Sun" and d.dominator == "Saturn")
        self.assertFalse(dom.has_counter_ray)
        self.assertEqual(dom.relationship, "square_decimation")

        self.assertTrue(merc.is_bonified)
        self.assertTrue(merc.is_maltreated)
        self.assertTrue(merc.benefic_enclosure_by_sign)

    def test_translation_and_malefic_enclosure_without_false_collection(self) -> None:
        planets = [
            _make_pos("Sun", 120.0, 1.0, house=10),
            _make_pos("Moon", 5.0, 13.0),
            _make_pos("Mercury", 350.0, 1.0),
            _make_pos("Venus", 140.0, 0.6),
            _make_pos("Mars", 275.0, -0.8),
            _make_pos("Jupiter", 310.0, 0.2),
            _make_pos("Saturn", 358.0, 0.05),
        ]
        reports, relationships = build_reports(_dummy_chart(), planets, _dummy_houses())
        self.assertTrue(any(t.translator == "Moon" for t in relationships.translations))

        # The old degree-only engine misread Mars 5 Capricorn / Saturn 28 Pisces
        # as a square and therefore manufactured a Saturn collection. Those signs
        # are sextile signs, and the actual sextile is outside the planetary orb.
        self.assertFalse(any(c.collector == "Saturn" for c in relationships.collections))

        jupiter_rep = next(r for r in reports if r.planet.name == "Jupiter")
        self.assertTrue(jupiter_rep.malefic_enclosure_by_sign)

    def test_collection_requires_collector_slower_than_both_feeders(self) -> None:
        collector = _make_pos("Saturn", 0.0, 0.05)
        fast = _make_pos("Mars", 58.0, 0.5)
        slow = _make_pos("Venus", 61.0, 0.2)
        planets = [_make_pos("Sun", 120.0, 1.0, house=10), collector, fast, slow]
        _reports, relationships = build_reports(_dummy_chart(), planets, _dummy_houses())

        # This scenario is about Saturn's attempted collection. Other planets in
        # the synthetic chart may independently satisfy collection with another
        # pair, which should not invalidate this assertion.
        self.assertFalse(any(c.collector == "Saturn" for c in relationships.collections))

    def test_fast_planet_cannot_collect(self) -> None:
        collector = _make_pos("Mercury", 0.0, 1.0)
        ven = _make_pos("Venus", 60.0, 0.8)
        mar = _make_pos("Mars", 120.0, 0.6)
        planets = [_make_pos("Sun", 180.0, 1.0, house=10), collector, ven, mar]
        _reports, relationships = build_reports(_dummy_chart(), planets, _dummy_houses())
        self.assertFalse(any(c.collector == "Mercury" for c in relationships.collections))

    def test_feral_detection_on_partial_planet_set(self) -> None:
        planets = [
            _make_pos("Sun", 0.0, 1.0, house=10),
            _make_pos("Venus", 30.0, 0.6),
            _make_pos("Mars", 330.0, -0.5),
            _make_pos("Saturn", 150.0, 0.05),
        ]
        reports, _relationships = build_reports(_dummy_chart(), planets, _dummy_houses())
        sun_rep = next(r for r in reports if r.planet.name == "Sun")
        self.assertTrue(sun_rep.is_feral)


if __name__ == "__main__":
    unittest.main()
