"""Directional odbojnost (repulsion), distinct from sign aversion."""

from __future__ import annotations

from itertools import permutations

from ..models import PlanetPosition, PlanetReport, RepulsionInfo
from .dignity import EXALTATIONS, SIGN_RULERS, sign_index_from_longitude


def _debilities_of_host_at_guest(host: str, guest_longitude: float) -> list[str]:
    """Return detriment/fall when guest occupies an enemy place of host."""

    sign = sign_index_from_longitude(guest_longitude)
    result: list[str] = []
    if SIGN_RULERS[(sign + 6) % 12] == host:
        result.append("detriment")
    if EXALTATIONS.get((sign + 6) % 12) == host:
        result.append("fall")
    return result


def compute_repulsions(
    reports: list[PlanetReport], planets: list[PlanetPosition]
) -> dict[str, dict[str, list[RepulsionInfo]]]:
    """Populate and return directional repulsion relationships.

    The course defines odbojnost when B occupies A's detriment or fall.  It is
    retained even if A also has minor dignity there, because the source
    explicitly allows mixed/bittersweet dignity-debility relationships.  An
    existing aspect is recorded but is not required to recognize the underlying
    directional condition.
    """

    report_by_name = {report.planet.name: report for report in reports}
    result = {
        planet.name: {"given": [], "received": []}
        for planet in planets
    }
    for host, guest in permutations(planets, 2):
        debilities = _debilities_of_host_at_guest(host.name, guest.longitude)
        if not debilities:
            continue
        host_report = report_by_name[host.name]
        aspect = next((asp for asp in host_report.aspects if asp.other == guest.name), None)
        info = RepulsionInfo(
            host=host.name,
            guest=guest.name,
            debilities=debilities,
            aspect_kind=aspect.kind if aspect else None,
        )
        result[host.name]["given"].append(info)
        result[guest.name]["received"].append(info)

    for report in reports:
        relation = result[report.planet.name]
        report.repulsions_given = relation["given"]
        report.repulsions_received = relation["received"]
    return result
