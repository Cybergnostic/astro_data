from __future__ import annotations

from typing import List, Tuple

from ..models import ChartInput, PlanetPosition, Houses, PlanetReport, ChartRelationships
from .dignity import essential_dignity, classify_speed, SIGNS
from .sect import chart_sect, planet_sect, compute_hayz_and_halb
from .stars import stars_near_longitude
from .aspects import aspects_for_planet
from ..synodic import compute_elongation_and_orientation, CAZIMI_ORB_DEG
from .relationships import aggregate_relationships


def build_reports(
    chart: ChartInput, planets: List[PlanetPosition], houses: Houses
) -> Tuple[List[PlanetReport], ChartRelationships]:
    """
    Build a full PlanetReport for each planet:
    - essential dignity (rulership, exaltation, triplicity, terms, faces)
    - sect, oriental/occidental, hayz/halb
    - speed class and ratio
    - fixed stars within orb
    - aspects to all other planets
    """
    # identify Sun and chart sect
    sun = next(p for p in planets if p.name == "Sun")
    sect_chart = chart_sect(sun.house)
    sun_long = sun.longitude

    reports: List[PlanetReport] = []
    for p in planets:
        # dignity
        ess = essential_dignity(p.name, p.longitude, is_day_chart=(sect_chart == "day"))

        # sect + oriental/occidental
        elong, oriental, occidental = compute_elongation_and_orientation(p.longitude, sun_long)
        if p.name == "Sun":
            oriental = False
            occidental = False
        is_cazimi = p.name != "Sun" and elong <= CAZIMI_ORB_DEG
        sect_plan = planet_sect(p.name, oriental)
        in_sect = sect_plan == sect_chart
        hayz, halb = compute_hayz_and_halb(p, sect_chart, sect_plan)

        # speed
        ratio, speed_class = classify_speed(p.name, p.speed_long)

        # fixed stars
        star_hits = stars_near_longitude(chart, p.longitude)

        # aspects
        aspect_list = aspects_for_planet(p, planets)

        reports.append(
            PlanetReport(
                planet=p,
                sign=ess["sign"],
                ruler=ess["ruler"],
                exaltation_lord=ess["exaltation_lord"],
                triplicity_lord=ess["triplicity_lord"],
                term_lord=ess["term_lord"],
                face_lord=ess["face_lord"],
                is_domicile=ess["is_domicile"],
                is_exalted=ess["is_exalted"],
                is_detriment=ess["is_detriment"],
                is_fall=ess["is_fall"],
                sect_chart=sect_chart,
                sect_planet=sect_plan,
                in_sect=in_sect,
                hayz=hayz,
                halb=halb,
                oriental=oriental,
                occidental=occidental,
                speed_ratio=ratio,
                speed_class=speed_class,
                fixed_stars=star_hits,
                aspects=aspect_list,
                bonification_sources=[],
                maltreatment_sources=[],
                is_bonified=False,
                is_maltreated=False,
                is_cazimi=is_cazimi,
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
        )

    relationships = aggregate_relationships(reports, planets, sect_chart == "day")
    return reports, relationships
