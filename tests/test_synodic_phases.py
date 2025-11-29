import unittest

from hor_tools.models import PlanetPosition
from hor_tools.synodic import compute_inferior_synodic_phase, compute_lunar_synodic_phase, compute_superior_synodic_phase


def _planet(name: str, longitude: float, speed_long: float) -> PlanetPosition:
    return PlanetPosition(
        name=name,
        longitude=longitude,
        latitude=0.0,
        speed_long=speed_long,
        speed_lat=0.0,
        house=1,
        retrograde=speed_long < 0,
    )


class SynodicPhasesTest(unittest.TestCase):
    def test_superior_synodic_phases(self) -> None:
        sun_long = 0.0

        self.assertEqual(
            compute_superior_synodic_phase(_planet("Mars", 50.0, 0.5), sun_long).code,
            "occidental_visible_direct_early",
        )
        self.assertEqual(
            compute_superior_synodic_phase(_planet("Jupiter", 80.0, 0.5), sun_long).code,
            "occidental_leaning",
        )
        self.assertEqual(
            compute_superior_synodic_phase(_planet("Saturn", 120.0, 0.5), sun_long).code,
            "occidental_strong",
        )

        # Retrograde approaching and around opposition on occidental side
        self.assertEqual(
            compute_superior_synodic_phase(_planet("Mars", 210.0, -0.2), sun_long).code,
            "retrograde_receding_or_pre_second_station",
        )
        self.assertEqual(
            compute_superior_synodic_phase(_planet("Mars", 185.0, -0.2), sun_long).code,
            "around_opposition",
        )

        # Oriental, retrograde and direct
        self.assertEqual(
            compute_superior_synodic_phase(_planet("Jupiter", 330.0, -0.2), sun_long).code,
            "retrograde_approaching_opposition",
        )
        self.assertEqual(
            compute_superior_synodic_phase(_planet("Saturn", 340.0, 0.0), sun_long).code,
            "first_station",
        )
        self.assertEqual(
            compute_superior_synodic_phase(_planet("Jupiter", 300.0, 0.3), sun_long).code,
            "oriental_far_before_station",
        )
        self.assertEqual(
            compute_superior_synodic_phase(_planet("Jupiter", 280.0, 0.3), sun_long).code,
            "oriental_weak",
        )

    def test_inferior_synodic_phases(self) -> None:
        sun_long = 0.0

        # Occidental side (ahead of Sun)
        self.assertEqual(compute_inferior_synodic_phase(_planet("Venus", 5.0, 0.4), sun_long).code, "combust_west")
        self.assertEqual(
            compute_inferior_synodic_phase(_planet("Mercury", 9.0, 0.4), sun_long).code, "under_beams_west_7_15"
        )
        self.assertEqual(
            compute_inferior_synodic_phase(_planet("Venus", 30.0, 0.4), sun_long).code,
            "occidental_visible_direct",
        )
        self.assertEqual(
            compute_inferior_synodic_phase(_planet("Mercury", 20.0, 0.0), sun_long).code,
            "first_station_west",
        )
        self.assertEqual(
            compute_inferior_synodic_phase(_planet("Venus", 30.0, -0.1), sun_long).code,
            "retrograde_west_towards_sun",
        )

        # Oriental side (behind the Sun)
        self.assertEqual(compute_inferior_synodic_phase(_planet("Venus", 355.0, 0.4), sun_long).code, "combust_east")
        self.assertEqual(
            compute_inferior_synodic_phase(_planet("Venus", 345.0, 0.4), sun_long).code, "under_beams_east"
        )
        self.assertEqual(
            compute_inferior_synodic_phase(_planet("Venus", 330.0, 0.4), sun_long).code,
            "oriental_strong_before_second_station",
        )
        self.assertEqual(
            compute_inferior_synodic_phase(_planet("Mercury", 330.0, 0.0), sun_long).code,
            "second_station_east",
        )
        self.assertEqual(
            compute_inferior_synodic_phase(_planet("Mercury", 330.0, -0.1), sun_long).code,
            "direct_east_closing",
        )
        self.assertEqual(
            compute_inferior_synodic_phase(_planet("Mercury", 345.0, -0.1), sun_long).code,
            "under_beams_east_return",
        )
        self.assertEqual(
            compute_inferior_synodic_phase(_planet("Mercury", 355.0, -0.1), sun_long).code,
            "combust_east_return",
        )

    def test_lunar_synodic_phases(self) -> None:
        sun_long = 0.0
        moon = "Moon"

        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 0.1, 0.5), sun_long).code, "cazimi")
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 4.0, 0.5), sun_long).code, "combust")
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 8.0, 0.5), sun_long).code, "under_beams")
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 30.0, 0.5), sun_long).code, "waxing_crescent")
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 70.0, 0.5), sun_long).code, "waxing_quarter")
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 120.0, 0.5), sun_long).code, "waxing_gibbous")
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 150.0, 0.5), sun_long).code, "waxing_near_full")
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 175.0, 0.5), sun_long).code, "full")

        # Waning side (west of Sun)
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 210.0, 0.5), sun_long).code, "waning_near_full")
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 240.0, 0.5), sun_long).code, "waning_gibbous")
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 270.0, 0.5), sun_long).code, "waning_quarter")
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 330.0, 0.5), sun_long).code, "waning_crescent")
        self.assertEqual(compute_lunar_synodic_phase(_planet(moon, 355.0, 0.5), sun_long).code, "combust_west")


if __name__ == "__main__":
    unittest.main()
