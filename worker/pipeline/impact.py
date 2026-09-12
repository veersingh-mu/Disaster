"""Settlement impact analysis and plain-language summary generation.

Performs spatial proximity/intersection between time-stepped flood extent
polygons and reference settlements, calculating arrival times and maximum depths.
"""

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import UUID

from worker.pipeline.routing import FloodTimeStepOutput


@dataclass
class AffectedSettlementResult:
    """Represents an impacted settlement with arrival time and depth."""
    settlement_id: UUID
    name: str
    district: str
    state: str
    population: Optional[int]
    arrival_time_minutes: int
    estimated_depth_m: float
    distance_km: float


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance between two points in kilometers."""
    r = 6371.0  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2) + (
        math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def point_in_polygon(x: float, y: float, polygon: List[List[float]]) -> bool:
    """Ray casting algorithm for testing if point (x=lon, y=lat) is in polygon."""
    n = len(polygon)
    inside = False
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def assess_settlement_impacts(
    origin_lat: float,
    origin_lon: float,
    time_steps: List[FloodTimeStepOutput],
    settlements_list: List[Dict[str, Any]],
    corridor_buffer_km: float = 5.5,
) -> List[AffectedSettlementResult]:
    """Calculate arrival time and inundation depth for each downstream settlement.

    Parameters:
    - origin_lat, origin_lon: Breach location coordinates.
    - time_steps: Ordered list of time-stepped simulation outputs.
    - settlements_list: Dicts containing id, name, latitude, longitude, district, state, population.
    - corridor_buffer_km: Buffer threshold distance from the advancing wave front.

    Returns:
    - List of AffectedSettlementResult sorted by arrival_time_minutes.
    """
    if not time_steps or not settlements_list:
        return []

    max_sim_dist_km = time_steps[-1].front_distance_km
    affected: List[AffectedSettlementResult] = []

    for s in settlements_list:
        s_lat = s["latitude"]
        s_lon = s["longitude"]
        dist_from_origin_km = haversine_distance_km(origin_lat, origin_lon, s_lat, s_lon)

        # Check if settlement lies within reach of the maximum simulation distance
        if dist_from_origin_km > (max_sim_dist_km + corridor_buffer_km):
            continue

        # Check intersection against time step polygons or closest wave front
        arrival_step: Optional[FloodTimeStepOutput] = None

        for step in time_steps:
            if step.time_step_minutes == 0:
                continue

            # Test: point in polygon or within corridor buffer distance
            is_inside = False
            min_dist_to_corridor = 9999.0

            for poly in step.polygon_coordinates:
                outer_ring = poly[0]
                if point_in_polygon(s_lon, s_lat, outer_ring):
                    is_inside = True
                    break
                for pt in outer_ring:
                    d_pt = haversine_distance_km(pt[1], pt[0], s_lat, s_lon)
                    if d_pt < min_dist_to_corridor:
                        min_dist_to_corridor = d_pt

            if is_inside or min_dist_to_corridor <= corridor_buffer_km:
                arrival_step = step
                break

        if arrival_step is not None:
            # Estimate precise arrival time between time steps
            arrival_min = max(5, int(arrival_step.time_step_minutes * (dist_from_origin_km / max(1.0, arrival_step.front_distance_km))))
            # Estimate local depth
            depth_est = max(0.8, round(arrival_step.max_depth_m * 0.75, 1))

            affected.append(AffectedSettlementResult(
                settlement_id=s["id"],
                name=s["name"],
                district=s["district"],
                state=s["state"],
                population=s.get("population"),
                arrival_time_minutes=arrival_min,
                estimated_depth_m=depth_est,
                distance_km=round(dist_from_origin_km, 1),
            ))

    # Sort strictly by arrival time
    affected.sort(key=lambda item: item.arrival_time_minutes)
    return affected


def generate_plain_language_summary(
    affected_settlements: List[AffectedSettlementResult],
    peak_depth_m: float,
) -> str:
    """Generate an actionable executive evacuation summary per the PRD requirements."""
    if not affected_settlements:
        return "No downstream settlements are in the projected inundation path within the simulation radius."

    count = len(affected_settlements)
    first = affected_settlements[0]

    summary_lines = [
        f"CRITICAL FLOOD ADVISORY: {count} settlement{'s' if count > 1 else ''} in the downstream inundation path.",
        f"First impact anticipated at {first.name} ({first.district}, {first.state}) in approximately {first.arrival_time_minutes} minutes with depths up to {first.estimated_depth_m}m.",
    ]

    immediate_evac = [s.name for s in affected_settlements if s.arrival_time_minutes <= 60]
    if immediate_evac:
        summary_lines.append(f"Immediate evacuation priority (< 60 min window): {', '.join(immediate_evac)}.")

    return " ".join(summary_lines)
