import unittest

from hor_tools.almuten import phase_score
from hor_tools.models import PlanetPosition


def _planet(
    name: str,
    longitude: float,
    speed_long: float,
    station: str | None = None,
) -> PlanetPosition:
    return PlanetPosition(
        name=name,
        longitude=longitude,
        latitude=0.0,
        speed_long=speed_long,
        speed_lat=0.0,
        house=1,
        retrograde=speed_long < 0,
        station=station,
    )


class PhaseScoringTest(unittest.TestCase):
    def test_ezra_phase_scoring_bands_on_oriental_separating_half(self) -> None:
        sun_long = 0.0

        # Superior planet behind the Sun: the Sun is separating from it.
        self.assertEqual(phase_score(_planet("Mars", 320.0, 0.5), sun_long), 3)
        self.assertEqual(phase_score(_planet("Jupiter", 285.0, 0.5), sun_long), 2)
        self.assertEqual(phase_score(_planet("Saturn", 260.0, 0.5), sun_long), 1)
        self.assertEqual(phase_score(_planet("Mars", 350.0, 0.5), sun_long), 0)
        self.assertEqual(phase_score(_planet("Jupiter", 320.0, -0.1), sun_long), 0)

        for name in ("Sun", "Moon", "Mercury", "Venus"):
            self.assertEqual(phase_score(_planet(name, 320.0, 0.5), sun_long), 0)

    def test_occidental_return_half_gets_no_ezra_bonus(self) -> None:
        sun_long = 0.0
        self.assertEqual(phase_score(_planet("Mars", 40.0, 0.5), sun_long), 0)
        self.assertEqual(phase_score(_planet("Jupiter", 75.0, 0.5), sun_long), 0)
        self.assertEqual(phase_score(_planet("Saturn", 100.0, 0.5), sun_long), 0)

    def test_first_station_ends_the_one_point_band(self) -> None:
        sun_long = 0.0
        self.assertEqual(phase_score(_planet("Saturn", 250.0, 0.01, station="first"), sun_long), 0)

    def test_no_decimal_gaps_between_ezra_bands(self) -> None:
        sun_long = 0.0
        self.assertEqual(phase_score(_planet("Mars", 300.0, 0.5), sun_long), 3)
        self.assertEqual(phase_score(_planet("Mars", 299.5, 0.5), sun_long), 2)
        self.assertEqual(phase_score(_planet("Mars", 270.0, 0.5), sun_long), 2)
        self.assertEqual(phase_score(_planet("Mars", 269.5, 0.5), sun_long), 1)


if __name__ == "__main__":
    unittest.main()
