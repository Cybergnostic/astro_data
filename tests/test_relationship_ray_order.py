from hor_tools.analysis.relationships import (
    compute_collection_of_light,
    compute_enclosures,
    compute_translation_of_light,
)
from hor_tools.models import AspectInfo, PlanetPosition


def planet(name: str, lon: float, speed: float) -> PlanetPosition:
    return PlanetPosition(
        name=name,
        longitude=lon,
        latitude=0.0,
        speed_long=speed,
        speed_lat=0.0,
        house=1,
        retrograde=speed < 0,
    )


def aspect(other: str, kind: str, *, applying: bool) -> AspectInfo:
    return AspectInfo(
        other=other,
        kind=kind,
        orb=1.0,
        applying=applying,
        dexter=False,
        self_applying=applying,
    )


def test_translation_is_cut_by_intervening_fourth_planet_ray() -> None:
    moon = planet("Moon", 10.0, 13.0)
    venus = planet("Venus", 8.0, 0.6)
    jupiter = planet("Jupiter", 15.0, 0.2)
    mars = planet("Mars", 12.0, 0.5)  # body/ray lies before Jupiter's conjunction point
    lookup = {
        ("Moon", "Venus"): aspect("Venus", "conjunction", applying=False),
        ("Moon", "Jupiter"): aspect("Jupiter", "conjunction", applying=True),
    }

    translations = compute_translation_of_light([moon, venus, jupiter, mars], lookup)
    assert not any(t.translator == "Moon" and t.to_planet == "Jupiter" for t in translations)


def test_translation_allows_a_ray_after_the_intended_contact() -> None:
    moon = planet("Moon", 10.0, 13.0)
    venus = planet("Venus", 8.0, 0.6)
    jupiter = planet("Jupiter", 15.0, 0.2)
    mars = planet("Mars", 18.0, 0.5)
    lookup = {
        ("Moon", "Venus"): aspect("Venus", "conjunction", applying=False),
        ("Moon", "Jupiter"): aspect("Jupiter", "conjunction", applying=True),
    }

    translations = compute_translation_of_light([moon, venus, jupiter, mars], lookup)
    assert any(t.translator == "Moon" and t.to_planet == "Jupiter" for t in translations)


def test_translation_not_rejected_merely_because_principals_also_aspect() -> None:
    moon = planet("Moon", 10.0, 13.0)
    venus = planet("Venus", 8.0, 0.6)
    jupiter = planet("Jupiter", 15.0, 0.2)
    lookup = {
        ("Moon", "Venus"): aspect("Venus", "conjunction", applying=False),
        ("Moon", "Jupiter"): aspect("Jupiter", "conjunction", applying=True),
        ("Venus", "Jupiter"): aspect("Jupiter", "conjunction", applying=True),
    }

    translations = compute_translation_of_light([moon, venus, jupiter], lookup)
    assert any(t.translator == "Moon" and t.to_planet == "Jupiter" for t in translations)


def test_collection_is_cut_when_feeder_contacts_other_feeder_first() -> None:
    collector = planet("Saturn", 20.0, 0.05)
    moon = planet("Moon", 10.0, 13.0)
    venus = planet("Venus", 12.0, 0.6)
    lookup = {
        ("Moon", "Saturn"): aspect("Saturn", "conjunction", applying=True),
        ("Venus", "Saturn"): aspect("Saturn", "conjunction", applying=True),
    }

    collections = compute_collection_of_light([collector, moon, venus], lookup)
    assert not any(c.collector == "Saturn" for c in collections)


def test_collection_survives_when_collector_is_next_contact_for_both_feeders() -> None:
    collector = planet("Saturn", 20.0, 0.05)
    moon = planet("Moon", 10.0, 13.0)
    venus = planet("Venus", 25.0, -0.6)
    lookup = {
        ("Moon", "Saturn"): aspect("Saturn", "conjunction", applying=True),
        ("Venus", "Saturn"): aspect("Saturn", "conjunction", applying=True),
    }

    collections = compute_collection_of_light([collector, moon, venus], lookup)
    assert any(c.collector == "Saturn" for c in collections)


def test_degree_enclosure_uses_ray_landing_points_not_caster_bodies() -> None:
    target = planet("Mercury", 258.0, 1.0)  # 18 Sagittarius
    venus = planet("Venus", 135.0, 0.6)     # trine ray at 255
    jupiter = planet("Jupiter", 142.0, 0.2) # trine ray at 262

    enclosure = compute_enclosures([target, venus, jupiter], {})["Mercury"]
    assert enclosure["benefic_ray"] == ["Venus", "Jupiter"]


def test_intervening_third_ray_breaks_degree_enclosure() -> None:
    target = planet("Mercury", 258.0, 1.0)
    venus = planet("Venus", 135.0, 0.6)     # ray 255
    jupiter = planet("Jupiter", 142.0, 0.2) # ray 262
    mars = planet("Mars", 260.0, 0.5)       # intervening body/ray ahead

    enclosure = compute_enclosures([target, venus, jupiter, mars], {})["Mercury"]
    assert enclosure["benefic_ray"] == []


def test_close_sun_or_benefic_aspect_relives_malefic_enclosure() -> None:
    target = planet("Mercury", 258.0, 1.0)
    mars = planet("Mars", 135.0, 0.5)       # trine ray at 255
    saturn = planet("Saturn", 142.0, 0.05)  # trine ray at 262
    sun = planet("Sun", 0.0, 1.0)
    lookup = {
        ("Mercury", "Sun"): AspectInfo(
            other="Sun",
            kind="trine",
            orb=6.0,
            applying=False,
            dexter=False,
            self_applying=False,
        )
    }

    enclosure = compute_enclosures([target, mars, saturn, sun], lookup)["Mercury"]
    assert enclosure["malefic_ray"] == []
