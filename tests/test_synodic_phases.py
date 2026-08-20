import unittest

from hor_tools.models import PlanetPosition
from hor_tools.synodic import (
    CAZIMI_ORB_DEG,
    compute_inferior_synodic_phase,
    compute_lunar_synodic_phase,
    compute_superior_synodic_phase,
    is_true_cazimi,
)


def _planet(
    name: str,
    longitude: float,
    speed_long: float,
    latitude: float = 0.0,
    station: str | None = None,
) -> PlanetPosition:
    return PlanetPosition(
        name=name,
        longitude=longitude,
        latitude=latitude,
        speed_long=speed_long,
        speed_lat=0.0,
        house=1,
        retrograde=speed_long < 0,
        station=station,
    )


class SynodicPhasesTest(unittest.TestCase):
    def test_superior_oriental_sequence(self) -> None:
        sun_long = 0.0
        self.assertEqual(compute_superior_synodic_phase(_planet("Jupiter", 310.0, 0.3), sun_long).index, 4)
        self.assertEqual(compute_superior_synodic_phase(_planet("Jupiter", 285.0, 0.3), sun_long).index, 5)
        self.assertEqual(compute_superior_synodic_phase(_planet("Jupiter", 250.0, 0.3), sun_long).index, 6)
        self.assertEqual(compute_superior_synodic_phase(_planet("Saturn", 250.0, 0.01, station="first"), sun_long).index, 7)
        self.assertEqual(compute_superior_synodic_phase(_planet("Mars", 210.0, -0.2), sun_long).index, 8)
        self.assertEqual(compute_superior_synodic_phase(_planet("Mars", 180.0, -0.2), sun_long).index, 9)

    def test_superior_occidental_return_sequence(self) -> None:
        sun_long = 0.0
        self.assertEqual(compute_superior_synodic_phase(_planet("Mars", 150.0, -0.2), sun_long).index, 10)
        self.assertEqual(compute_superior_synodic_phase(_planet("Saturn", 120.0, -0.01, station="second"), sun_long).index, 11)
        self.assertEqual(compute_superior_synodic_phase(_planet("Saturn", 120.0, 0.2), sun_long).index, 12)
        self.assertEqual(compute_superior_synodic_phase(_planet("Jupiter", 80.0, 0.2), sun_long).index, 13)
        self.assertEqual(compute_superior_synodic_phase(_planet("Jupiter", 50.0, 0.2), sun_long).index, 14)
        self.assertEqual(compute_superior_synodic_phase(_planet("Jupiter", 20.0, 0.2), sun_long).index, 15)

    def test_superior_strong_easternization_runs_to_sixty_degrees(self) -> None:
        sun_long = 0.0
        self.assertEqual(compute_superior_synodic_phase(_planet("Jupiter", 300.0, 0.3), sun_long).code, "oriental_strong")
        self.assertEqual(compute_superior_synodic_phase(_planet("Jupiter", 299.9, 0.3), sun_long).code, "oriental_weak")
        self.assertEqual(compute_superior_synodic_phase(_planet("Jupiter", 270.0, 0.3), sun_long).code, "oriental_weak")
        self.assertEqual(compute_superior_synodic_phase(_planet("Jupiter", 269.9, 0.3), sun_long).code, "oriental_far_before_station")

    def test_inferior_occidental_sequence(self) -> None:
        sun_long = 0.0
        self.assertEqual(compute_inferior_synodic_phase(_planet("Venus", 5.0, 0.4), sun_long).index, 10)
        self.assertEqual(compute_inferior_synodic_phase(_planet("Mercury", 9.0, 0.4), sun_long).index, 11)
        self.assertEqual(compute_inferior_synodic_phase(_planet("Venus", 30.0, 0.4), sun_long).index, 12)
        self.assertEqual(compute_inferior_synodic_phase(_planet("Mercury", 30.0, 0.02, station="first"), sun_long).index, 13)
        self.assertEqual(compute_inferior_synodic_phase(_planet("Venus", 30.0, -0.1), sun_long).index, 14)
        self.assertEqual(compute_inferior_synodic_phase(_planet("Mercury", 9.0, -0.1), sun_long).index, 15)
        self.assertEqual(compute_inferior_synodic_phase(_planet("Mercury", 5.0, -0.1), sun_long).index, 16)

    def test_inferior_oriental_sequence_uses_retrograde_before_second_station(self) -> None:
        sun_long = 0.0
        self.assertEqual(compute_inferior_synodic_phase(_planet("Venus", 355.0, -0.1), sun_long).index, 2)
        self.assertEqual(compute_inferior_synodic_phase(_planet("Mercury", 345.0, -0.1), sun_long).index, 3)
        self.assertEqual(compute_inferior_synodic_phase(_planet("Venus", 330.0, -0.1), sun_long).index, 4)
        self.assertEqual(compute_inferior_synodic_phase(_planet("Mercury", 330.0, -0.01, station="second"), sun_long).index, 5)
        self.assertEqual(compute_inferior_synodic_phase(_planet("Mercury", 330.0, 0.4), sun_long).index, 6)
        self.assertEqual(compute_inferior_synodic_phase(_planet("Mercury", 345.0, 0.4), sun_long).index, 7)
        self.assertEqual(compute_inferior_synodic_phase(_planet("Mercury", 355.0, 0.4), sun_long).index, 8)

    def test_course_project_solar_ray_boundaries(self) -> None:
        sun_long = 0.0
        self.assertEqual(compute_inferior_synodic_phase(_planet("Mercury", 7.49, 0.4), sun_long).code, "combust_west")
        self.assertEqual(compute_inferior_synodic_phase(_planet("Mercury", 7.51, 0.4), sun_long).code, "under_beams_west")
        self.assertEqual(compute_inferior_synodic_phase(_planet("Mercury", 15.01, 0.4), sun_long).code, "occidental_visible_direct")
        self.assertEqual(compute_superior_synodic_phase(_planet("Mars", 7.49, 0.4), sun_long).code, "combust_west")
        self.assertEqual(compute_superior_synodic_phase(_planet("Mars", 7.51, 0.4), sun_long).code, "under_beams_west")

    def test_lunar_waxing_sequence(self) -> None:
        sun_long = 0.0
        moon = "Moon"
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 0.1, 0.5), sun_long).index, 1)
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 4.0, 0.5), sun_long).index, 2)
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 8.0, 0.5), sun_long).index, 3)
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 30.0, 0.5), sun_long).index, 4)
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 70.0, 0.5), sun_long).index, 5)
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 120.0, 0.5), sun_long).index, 6)
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 150.0, 0.5), sun_long).index, 7)
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 175.0, 0.5), sun_long).index, 8)
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 180.0, 0.5), sun_long).index, 9)

    def test_lunar_waning_return_sequence(self) -> None:
        sun_long = 0.0
        moon = "Moon"
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 185.0, 0.5), sun_long).index, 10)
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 210.0, 0.5), sun_long).index, 11)
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 240.0, 0.5), sun_long).index, 12)
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 300.0, 0.5), sun_long).index, 14)
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 345.0, 0.5), sun_long).index, 15)
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 355.0, 0.5), sun_long).index, 16)

    def test_true_cazimi_requires_latitude_too(self) -> None:
        sun = _planet("Sun", 100.0, 1.0, latitude=0.0)
        ordinary_and_true = _planet("Mercury", 100.2, 1.2, latitude=0.2)
        ordinary_but_not_true = _planet("Mercury", 100.2, 1.2, latitude=0.5)
        self.assertLessEqual(0.2, CAZIMI_ORB_DEG)
        self.assertTrue(is_true_cazimi(ordinary_and_true, sun))
        self.assertFalse(is_true_cazimi(ordinary_but_not_true, sun))


if __name__ == "__main__":
    unittest.main()
