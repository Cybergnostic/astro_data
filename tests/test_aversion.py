from hor_tools.analysis.aversion import compute_domicile_aversion
from hor_tools.models import (
    AspectInfo,
    DomicileAversion,
    PlanetPosition,
    PlanetReport,
    ReflectionHit,
    TranslationOfLight,
)


def make_planet(name: str, lon: float, speed: float = 1.0) -> PlanetPosition:
    return PlanetPosition(
        name=name,
        longitude=lon,
        latitude=0.0,
        speed_long=speed,
        speed_lat=0.0,
        house=1,
        retrograde=False,
    )


def empty_report_for(p: PlanetPosition) -> PlanetReport:
    return PlanetReport(
        planet=p,
        sign="",
        ruler=None,
        exaltation_lord=None,
        triplicity_lord=None,
        term_lord=None,
        face_lord=None,
        is_domicile=False,
        is_exalted=False,
        is_detriment=False,
        is_fall=False,
        sect_chart="day",
        sect_planet="day",
        in_sect=False,
        hayz=False,
        halb=False,
        oriental=False,
        occidental=False,
        speed_ratio=1.0,
        speed_class="average",
        fixed_stars=[],
        aspects=[],
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
        is_feral=False,
    )


def test_sees_domicile_when_in_whole_sign_aspect():
    mars = make_planet("Mars", 270.0)  # 0° Capricorn, square Aries domicile
    reports = [empty_report_for(mars)]
    compute_domicile_aversion(reports, [mars], translations=[])

    mars_aversion = reports[0].domicile_aversions
    aries_status = next(av for av in mars_aversion if av.domicile_sign == "Aries")
    assert aries_status.sees is True
    assert aries_status.avoided is False


def test_aversion_avoided_via_translation_with_planet_in_domicile():
    mercury = make_planet("Mercury", 270.0)  # Capricorn, aversion to Virgo/Gemini
    mars = make_planet("Mars", 170.0)  # 20° Virgo (Mercury domicile)
    sun = make_planet("Sun", 200.0)

    reports = [empty_report_for(mercury), empty_report_for(mars), empty_report_for(sun)]
    translation = TranslationOfLight(
        translator="Sun",
        from_planet="Mercury",
        to_planet="Mars",
        aspect_from=AspectInfo(other="Mercury", kind="trine", orb=0.5, applying=False, dexter=True),
        aspect_to=AspectInfo(other="Mars", kind="sextile", orb=0.5, applying=True, dexter=False),
        naturally_fastest=False,
    )

    compute_domicile_aversion(reports, [mercury, mars, sun], translations=[translation])

    virgo_status = next(av for av in reports[0].domicile_aversions if av.domicile_sign == "Virgo")
    assert virgo_status.sees is False
    assert virgo_status.avoided is True
    assert any("translation" in reason for reason in virgo_status.avoided_by)

    gemini_status = next(av for av in reports[0].domicile_aversions if av.domicile_sign == "Gemini")
    assert gemini_status.sees is False
    assert gemini_status.avoided is True


def test_aversion_avoided_by_sign_level_antiscia_or_contra():
    mars = make_planet("Mars", 165.0)  # 15° Virgo, aversion to Aries but antiscia pair
    reports = [empty_report_for(mars)]
    compute_domicile_aversion(reports, [mars], translations=[])

    aries_status = next(av for av in reports[0].domicile_aversions if av.domicile_sign == "Aries")
    assert aries_status.sees is False
    assert aries_status.avoided is True
    assert any("antiscia" in reason for reason in aries_status.avoided_by)
