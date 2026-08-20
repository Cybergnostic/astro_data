from hor_tools.analysis.natal_synthesis import build_behaviour_ruler
from hor_tools.models import AspectInfo, Houses, PlanetPosition, PlanetReport


def _planet(name: str, longitude: float, house: int = 2) -> PlanetPosition:
    return PlanetPosition(
        name=name,
        longitude=longitude,
        latitude=0.0,
        speed_long=1.0,
        speed_lat=0.0,
        house=house,
        retrograde=False,
    )


def _report(planet: PlanetPosition, aspects: list[AspectInfo] | None = None) -> PlanetReport:
    return PlanetReport(
        planet=planet,
        sign="Aries",
        ruler="Mars",
        exaltation_lord="Sun",
        triplicity_lord="Sun",
        term_lord="Jupiter",
        face_lord="Mars",
        is_domicile=False,
        is_exalted=False,
        is_detriment=False,
        is_fall=False,
        sect_chart="day",
        sect_planet="day",
        in_sect=True,
        hayz=False,
        halb=False,
        oriental=True,
        occidental=False,
        speed_ratio=1.0,
        speed_class="average",
        fixed_stars=[],
        aspects=aspects or [],
        antiscia_longitude=0.0,
        contra_antiscia_longitude=0.0,
        antiscia_hits=[],
        contra_antiscia_hits=[],
        domicile_aversions=[],
        bonification_sources=[],
        maltreatment_sources=[],
        is_bonified=False,
        is_maltreated=False,
        is_cazimi=False,
        benefic_enclosure_by_ray=False,
        malefic_enclosure_by_ray=False,
        benefic_enclosure_by_sign=False,
        malefic_enclosure_by_sign=False,
        dominations_over=[],
        dominated_by=[],
        receptions_given=[],
        receptions_received=[],
        generosities_given=[],
        generosities_received=[],
        repulsions_given=[],
        repulsions_received=[],
        is_feral=False,
    )


def _aspect(other: str, kind: str, orb: float) -> AspectInfo:
    return AspectInfo(
        other=other,
        kind=kind,
        orb=orb,
        applying=True,
        dexter=False,
    )


def test_competing_mercury_and_moon_conjunctions_require_judgment() -> None:
    mercury = _planet("Mercury", 30.0)
    moon = _planet("Moon", 60.0)
    venus = _planet("Venus", 31.0)
    jupiter = _planet("Jupiter", 60.5)
    mars = _planet("Mars", 120.0)

    reports = [
        _report(mercury, [_aspect("Venus", "conjunction", 1.0)]),
        _report(moon, [_aspect("Jupiter", "conjunction", 0.5)]),
        _report(venus),
        _report(jupiter),
        _report(mars),
    ]
    result = build_behaviour_ruler(
        [mercury, moon, venus, jupiter, mars],
        Houses(cusps=[0.0] + [float((i - 1) * 30) for i in range(1, 13)], asc=0.0, mc=270.0),
        reports,
    )

    assert result.primary is None
    assert result.secondary == "Mars"
    assert result.candidates == ["Jupiter", "Venus"]
    assert "qualitative comparison" in result.rule
    assert any("manual judgment required" in item for item in result.evidence)


def test_multiple_conjunctions_to_same_significator_use_closest_contact() -> None:
    mercury = _planet("Mercury", 30.0)
    moon = _planet("Moon", 60.0)
    venus = _planet("Venus", 32.0)
    jupiter = _planet("Jupiter", 31.0)
    mars = _planet("Mars", 120.0)

    reports = [
        _report(
            mercury,
            [
                _aspect("Venus", "conjunction", 2.0),
                _aspect("Jupiter", "conjunction", 1.0),
            ],
        ),
        _report(moon),
        _report(venus),
        _report(jupiter),
        _report(mars),
    ]
    result = build_behaviour_ruler(
        [mercury, moon, venus, jupiter, mars],
        Houses(cusps=[0.0] + [float((i - 1) * 30) for i in range(1, 13)], asc=0.0, mc=270.0),
        reports,
    )

    assert result.primary == "Jupiter"
    assert result.secondary == "Mars"
    assert result.candidates == ["Jupiter"]
    assert "conjunct Mercury, orb 1.00°" in result.evidence[0]
