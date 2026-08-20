from __future__ import annotations

from typing import List, Tuple

from ..models import ChartInput, PlanetPosition, Houses, PlanetReport, ChartRelationships
from .dignity import essential_dignity, classify_speed, SIGNS
from .sect import chart_sect, planet_sect, compute_hayz_and_halb
from .stars import stars_near_longitude
from .aspects import aspects_for_planet
from .antiscia import antiscia_longitude, contra_antiscia_longitude, reflection_hits_for_planet
from .aversion import compute_domicile_aversion
from .conditions import (
    is_in_planetary_joy,
    latitude_condition,
    is_in_via_combusta,
    moon_void_of_course,
)
from ..synodic import compute_elongation_and_orientation, CAZIMI_ORB_DEG, is_true_cazimi
from .relationship_rules import aggregate_relationships


def build_reports(
    chart: ChartInput, planets: List[PlanetPosition], houses: Houses
) -> Tuple[List[PlanetReport], ChartRelationships]:
    """
    Build a full PlanetReport for each planet:
    - essential dignity
    - true-horizon sect, hayz and halb
    - solar orientation and ordinary/strict cazimi
    - speed relative to the planet's mean
    - planetary joy, latitude testimony, via combusta and lunar void-of-course
    - fixed stars and aspects
    - chart-level relationship techniques
    """
    sun = next(p for p in planets if p.name == "Sun")
    moon = next(p for p in planets if p.name == "Moon")
    sect_chart = chart_sect(chart, sun)
    sun_long = sun.longitude

    # VOC is primarily a lunar condition in this report. Compute it once from
    # future ephemeris positions rather than recomputing it for every planet.
    moon_voc = moon_void_of_course(chart, moon)

    reports: List[PlanetReport] = []
    for p in planets:
        ess = essential_dignity(p.name, p.longitude, is_day_chart=(sect_chart == "day"))

        elong, oriental, occidental = compute_elongation_and_orientation(p.longitude, sun_long)
        if p.name == "Sun":
            oriental = False
            occidental = False
        ordinary_cazimi = p.name != "Sun" and elong <= CAZIMI_ORB_DEG
        strict_cazimi = is_true_cazimi(p, sun)
        sect_plan = planet_sect(p.name, oriental)
        in_sect = sect_plan == sect_chart
        hayz, halb = compute_hayz_and_halb(p, chart, sect_chart, sect_plan)

        ratio, speed_class = classify_speed(p.name, p.speed_long)
        star_hits = stars_near_longitude(chart, p.longitude)
        aspect_list = aspects_for_planet(p, planets)
        antiscia_target = antiscia_longitude(p.longitude)
        contra_target = contra_antiscia_longitude(p.longitude)
        antiscia_hits, contra_hits = reflection_hits_for_planet(p, planets)

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
                antiscia_longitude=antiscia_target,
                contra_antiscia_longitude=contra_target,
                antiscia_hits=antiscia_hits,
                contra_antiscia_hits=contra_hits,
                domicile_aversions=[],
                bonification_sources=[],
                maltreatment_sources=[],
                is_bonified=False,
                is_maltreated=False,
                is_cazimi=ordinary_cazimi,
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
                is_true_cazimi=strict_cazimi,
                is_in_planetary_joy=is_in_planetary_joy(p),
                latitude_condition=latitude_condition(p),
                is_in_via_combusta=is_in_via_combusta(p.longitude),
                is_void_of_course=(p.name == "Moon" and moon_voc),
            )
        )

    relationships = aggregate_relationships(reports, planets, sect_chart == "day")
    compute_domicile_aversion(reports, planets, relationships.translations)
    return reports, relationships
