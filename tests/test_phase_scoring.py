import unittest

from hor_tools.almuten import phase_score
from hor_tools.models import PlanetPosition


def _planet(name: str, longitude: float, speed_long: float) -> PlanetPosition:
    return PlanetPosition(
        name=name,
        longitude=longitude,
        latitude=0.0,
        speed_long=speed_long,
        speed_lat=0.0,
        house=1,
        retrograde=speed_long <= 0,
    )


class PhaseScoringTest(unittest.TestCase):
    def test_ezra_phase_scoring_bands(self) -> None:
        sun_long = 0.0

        self.assertEqual(phase_score(_planet("Mars", 40.0, 0.5), sun_long), 3)
        self.assertEqual(phase_score(_planet("Jupiter", 75.0, 0.5), sun_long), 2)
        self.assertEqual(phase_score(_planet("Saturn", 100.0, 0.5), sun_long), 1)
        self.assertEqual(phase_score(_planet("Mars", 10.0, 0.5), sun_long), 0)
        self.assertEqual(phase_score(_planet("Jupiter", 40.0, -0.1), sun_long), 0)

        for name in ("Sun", "Moon", "Mercury", "Venus"):
            self.assertEqual(phase_score(_planet(name, 40.0, 0.5), sun_long), 0)

    def test_no_decimal_gaps_between_ezra_bands(self) -> None:
        sun_long = 0.0
        self.assertEqual(phase_score(_planet("Mars", 60.0, 0.5), sun_long), 3)
        self.assertEqual(phase_score(_planet("Mars", 60.5, 0.5), sun_long), 2)
        self.assertEqual(phase_score(_planet("Mars", 90.0, 0.5), sun_long), 2)
        self.assertEqual(phase_score(_planet("Mars", 90.5, 0.5), sun_long), 1)


if __name__ == "__main__":
    unittest.main()
