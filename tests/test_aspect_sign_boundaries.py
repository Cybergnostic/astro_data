import unittest

from hor_tools.analysis.aspects import aspects_for_planet
from hor_tools.models import PlanetPosition


def _planet(name: str, longitude: float, speed: float = 1.0) -> PlanetPosition:
    return PlanetPosition(
        name=name,
        longitude=longitude,
        latitude=0.0,
        speed_long=speed,
        speed_lat=0.0,
        house=1,
        retrograde=speed < 0,
    )


def _aspect(source: PlanetPosition, target: PlanetPosition):
    aspects = aspects_for_planet(source, [source, target])
    return aspects[0] if aspects else None


class AspectSignBoundaryTest(unittest.TestCase):
    def test_sign_relation_blocks_geometrically_nearer_wrong_aspect(self) -> None:
        # 28 Taurus / 7 Aquarius: the signs are square, but the degree distance
        # is geometrically closer to a trine. The course says there is no degree
        # contact yet; the square only begins once the Moon reaches the Sun's orb.
        sun = _planet("Sun", 58.0, 1.0)
        moon = _planet("Moon", 307.0, 13.0)
        self.assertIsNone(_aspect(sun, moon))

    def test_current_sign_configuration_enters_planetary_orb(self) -> None:
        # 28 Taurus / 13 Aquarius is exactly 15° from the square branch and is
        # therefore the beginning of contact under the Sun's 15° orb.
        sun = _planet("Sun", 58.0, 1.0)
        moon = _planet("Moon", 313.0, 13.0)
        aspect = _aspect(sun, moon)
        self.assertIsNotNone(aspect)
        self.assertEqual(aspect.kind, "square")
        self.assertAlmostEqual(aspect.orb, 15.0)

    def test_old_configuration_can_continue_across_boundary_within_three_degrees(self) -> None:
        # 29 Taurus / 1 Aquarius: the Moon has crossed out of the trine signs,
        # but the old trine is only 2° from exact and remains valid by exception.
        sun = _planet("Sun", 59.0, 1.0)
        moon = _planet("Moon", 301.0, 13.0)
        aspect = _aspect(sun, moon)
        self.assertIsNotNone(aspect)
        self.assertEqual(aspect.kind, "trine")
        self.assertAlmostEqual(aspect.orb, 2.0)

    def test_old_configuration_dies_beyond_three_degrees(self) -> None:
        # 28 Taurus / 2 Aquarius leaves the old trine 4° from exact; the current
        # square is still far outside the Sun's orb, so there is no contact.
        sun = _planet("Sun", 58.0, 1.0)
        moon = _planet("Moon", 302.0, 13.0)
        self.assertIsNone(_aspect(sun, moon))

    def test_out_of_sign_conjunction_allowed_within_three_degrees(self) -> None:
        mercury = _planet("Mercury", 89.0, 1.2)  # 29 Gemini
        venus = _planet("Venus", 91.0, 1.0)      # 1 Cancer
        aspect = _aspect(mercury, venus)
        self.assertIsNotNone(aspect)
        self.assertEqual(aspect.kind, "conjunction")
        self.assertAlmostEqual(aspect.orb, 2.0)

    def test_out_of_sign_conjunction_rejected_beyond_three_degrees(self) -> None:
        mercury = _planet("Mercury", 87.0, 1.2)  # 27 Gemini
        venus = _planet("Venus", 91.0, 1.0)      # 1 Cancer
        self.assertIsNone(_aspect(mercury, venus))


if __name__ == "__main__":
    unittest.main()
