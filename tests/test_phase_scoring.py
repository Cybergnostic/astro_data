import unittest

from hor_tools.almuten import HOUSE_STRENGTH_SCORES, phase_score
from hor_tools.models import PlanetPosition


def _planet(
    name: str,
    longitude: float,
    speed_long: float = 0.5,
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
    def test_teacher_chart_matches_morinus_phase_table(self) -> None:
        # Teacher-configured Morinus output for 1988-06-08 19:15 Nis:
        # Saturn=0, Jupiter=1, Mars=2.
        sun = 60.0 + 18.0 + 6.0 / 60.0 + 33.0 / 3600.0
        jupiter = 30.0 + 21.0 + 16.0 / 60.0 + 23.0 / 3600.0
        mars = 330.0 + 10.0 + 51.0 / 60.0 + 32.0 / 3600.0
        saturn = 270.0 + 6.0 / 60.0 + 28.0 / 3600.0

        self.assertEqual(1, phase_score(_planet("Jupiter", jupiter), sun))
        self.assertEqual(2, phase_score(_planet("Mars", mars), sun))
        self.assertEqual(0, phase_score(_planet("Saturn", saturn, -0.01), sun))

    def test_morinus_directional_sun_phase_bands(self) -> None:
        sun = 0.0
        # Directional separation is (Sun - superior) mod 360.
        self.assertEqual(1, phase_score(_planet("Mars", 336.0), sun))   # 24 deg: weak
        self.assertEqual(2, phase_score(_planet("Mars", 325.0), sun))   # 35 deg: medium
        self.assertEqual(3, phase_score(_planet("Mars", 300.0), sun))   # 60 deg: strong
        self.assertEqual(2, phase_score(_planet("Mars", 270.0), sun))   # 90 deg: medium
        self.assertEqual(1, phase_score(_planet("Mars", 250.0), sun))   # 110 deg: weak
        self.assertEqual(0, phase_score(_planet("Mars", 230.0), sun))   # 130 deg: none

    def test_morinus_phase_is_not_absolute_elongation(self) -> None:
        sun = 0.0
        # Same 24-degree absolute separation on the opposite side gets no score.
        self.assertEqual(1, phase_score(_planet("Jupiter", 336.0), sun))
        self.assertEqual(0, phase_score(_planet("Jupiter", 24.0), sun))

    def test_morinus_phase_source_does_not_filter_by_motion(self) -> None:
        sun = 0.0
        self.assertEqual(1, phase_score(_planet("Saturn", 336.0, -0.1), sun))
        self.assertEqual(1, phase_score(_planet("Saturn", 336.0, 0.0, station="first"), sun))

    def test_exact_morinus_band_edges_are_unscored(self) -> None:
        sun = 0.0
        # almutens.py uses strict inequalities in inorbsinister(), so the
        # exact boundaries fall into neither adjacent interval.
        for separation in (18.0, 30.0, 40.0, 80.0, 100.0, 120.0):
            longitude = (-separation) % 360.0
            self.assertEqual(0, phase_score(_planet("Mars", longitude), sun))

    def test_only_superior_planets_receive_phase_points(self) -> None:
        sun = 0.0
        for name in ("Sun", "Moon", "Mercury", "Venus"):
            self.assertEqual(0, phase_score(_planet(name, 300.0), sun))

    def test_teacher_morinus_house_scores(self) -> None:
        self.assertEqual(
            {
                1: 12,
                2: 6,
                3: 3,
                4: 9,
                5: 7,
                6: 1,
                7: 10,
                8: 4,
                9: 5,
                10: 11,
                11: 8,
                12: 2,
            },
            HOUSE_STRENGTH_SCORES,
        )


if __name__ == "__main__":
    unittest.main()
