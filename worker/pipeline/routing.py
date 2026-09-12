"""Simplified 2D hydrodynamic & diffusive-wave flood routing engine.

Simulates dam/lake breach flood wave propagation through downstream river corridors
using Manning's velocity equation, wave celerity, and discharge attenuation.
Generates time-stepped inundation polygons (GeoJSON MultiPolygon) and maximum depths.
"""

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from worker.pipeline.breach import BreachParameters
from worker.pipeline.dem import DEMProfile


@dataclass
class FloodTimeStepOutput:
    """Inundation footprint at a specific elapsed time step."""
    time_step_minutes: int
    max_depth_m: float
    front_distance_km: float
    front_latitude: float
    front_longitude: float
    polygon_coordinates: List[List[List[List[float]]]]  # GeoJSON MultiPolygon structure
    wkt_geometry: str


def meters_to_lat_lon_offsets(
    distance_meters: float,
    azimuth_deg: float,
    origin_lat: float,
) -> Tuple[float, float]:
    """Calculate latitude and longitude offsets given distance and bearing."""
    azimuth_rad = math.radians(azimuth_deg)
    dx = distance_meters * math.sin(azimuth_rad)
    dy = distance_meters * math.cos(azimuth_rad)

    # 1 degree lat ~ 111,320m
    lat_offset = dy / 111320.0
    # 1 degree lon ~ 111,320m * cos(lat)
    lon_offset = dx / (111320.0 * math.cos(math.radians(origin_lat)))
    return lat_offset, lon_offset


def generate_corridor_multipolygon(
    waypoints: List[Tuple[float, float]],
    widths: List[float],
) -> Tuple[List[List[List[List[float]]]], str]:
    """Generate a clean polygon strip around a river centerline with variable width."""
    if len(waypoints) < 2:
        # Trivial seed box around origin
        lon, lat = waypoints[0]
        w_deg = (widths[0] / 111320.0)
        ring = [
            [lon - w_deg, lat - w_deg],
            [lon + w_deg, lat - w_deg],
            [lon + w_deg, lat + w_deg],
            [lon - w_deg, lat + w_deg],
            [lon - w_deg, lat - w_deg],
        ]
        coords = [[ring]]
        wkt = f"SRID=4326;MULTIPOLYGON((({lon - w_deg} {lat - w_deg}, {lon + w_deg} {lat - w_deg}, {lon + w_deg} {lat + w_deg}, {lon - w_deg} {lat + w_deg}, {lon - w_deg} {lat - w_deg})))"
        return coords, wkt

    left_bank = []
    right_bank = []

    for i in range(len(waypoints)):
        lon, lat = waypoints[i]
        half_w = max(30.0, widths[i] / 2.0)
        half_w_deg_lat = half_w / 111320.0
        half_w_deg_lon = half_w / (111320.0 * max(0.2, math.cos(math.radians(lat))))

        if i < len(waypoints) - 1:
            next_lon, next_lat = waypoints[i + 1]
            dx = (next_lon - lon)
            dy = (next_lat - lat)
        else:
            prev_lon, prev_lat = waypoints[i - 1]
            dx = (lon - prev_lon)
            dy = (lat - prev_lat)

        length = math.hypot(dx, dy)
        if length > 0:
            nx = -dy / length
            ny = dx / length
        else:
            nx, ny = 0.0, 1.0

        left_bank.append([round(lon + nx * half_w_deg_lon, 5), round(lat + ny * half_w_deg_lat, 5)])
        right_bank.append([round(lon - nx * half_w_deg_lon, 5), round(lat - ny * half_w_deg_lat, 5)])

    # Construct outer ring: left bank forward + right bank backward + close ring
    outer_ring = left_bank + list(reversed(right_bank))
    outer_ring.append(left_bank[0])  # close ring

    # Standard GeoJSON MultiPolygon structure: [ [ [ [lon, lat], ... ] ] ]
    geojson_coords = [[outer_ring]]

    # WKT MultiPolygon
    wkt_points = ", ".join(f"{pt[0]} {pt[1]}" for pt in outer_ring)
    wkt_str = f"SRID=4326;MULTIPOLYGON((({wkt_points})))"

    return geojson_coords, wkt_str


def simulate_flood_routing(
    origin_lat: float,
    origin_lon: float,
    breach: BreachParameters,
    dem: DEMProfile,
    simulation_radius_km: float = 45.0,
    time_steps_minutes: Optional[List[int]] = None,
) -> List[FloodTimeStepOutput]:
    """Execute simplified 2D diffusive-wave flood routing.

    Returns a list of FloodTimeStepOutput corresponding to each time step.
    """
    if time_steps_minutes is None:
        time_steps_minutes = [0, 15, 30, 45, 60, 90, 120, 180, 240, 330]

    # Manning's roughness n (0.055 for rugged mountain boulder gorges)
    manning_n = 0.055
    slope = max(0.005, dem.channel_slope_m_per_m)

    # Initial peak hydraulic depth h0 from discharge and breach width
    # Q ~ (1/n) * B * h^(5/3) * S^(1/2) -> h ~ ( (Q * n) / (B * S^0.5) ) ^ (3/5)
    width_0 = max(20.0, breach.breach_width_m)
    # Stoker/Ritter dam break initial release depth combined with Manning equation
    manning_depth = ((breach.peak_discharge_m3s * manning_n) / (width_0 * math.sqrt(slope))) ** 0.6
    h_initial = max(manning_depth, min(50.0, 5.0 + math.sqrt(breach.peak_discharge_m3s) * 0.28))
    if breach.peak_discharge_m3s > 5000.0:
        h_initial = max(20.0, h_initial)

    results: List[FloodTimeStepOutput] = []

    # Downstream river trajectory waypoints
    # Main valley bearing with natural curvature and sinuosity
    base_azimuth = dem.valley_aspect_deg

    for t_min in time_steps_minutes:
        if t_min == 0:
            # Breach origin snapshot
            wp = [(origin_lon, origin_lat)]
            w = [width_0]
            coords, wkt = generate_corridor_multipolygon(wp, w)
            results.append(FloodTimeStepOutput(
                time_step_minutes=0,
                max_depth_m=round(h_initial, 1),
                front_distance_km=0.0,
                front_latitude=origin_lat,
                front_longitude=origin_lon,
                polygon_coordinates=coords,
                wkt_geometry=wkt,
            ))
            continue

        # Elapsed time in seconds
        t_sec = t_min * 60.0

        # Mean velocity through gorge: v = (1/n) * R^(2/3) * S^(1/2)
        # Wave celerity c = 5/3 * v (kinematic wave)
        # In mountainous steep channel: v ~ 6 to 12 m/s, c ~ 10 to 18 m/s
        v_current = (1.0 / manning_n) * (h_initial ** 0.667) * math.sqrt(slope)
        v_current = max(4.0, min(18.0, v_current))
        celerity = (5.0 / 3.0) * v_current

        # Front distance with progressive attenuation
        dist_m = min(simulation_radius_km * 1000.0, celerity * t_sec * 0.82)
        dist_km = dist_m / 1000.0

        # Hydraulic attenuation: depth decays along channel
        h_current = max(1.5, h_initial / (1.0 + (0.032 * dist_km)))

        # Build trajectory waypoints from origin to wave front
        num_segments = max(4, int(dist_km / 1.5))
        waypoints = []
        widths = []

        for seg in range(num_segments + 1):
            frac = seg / num_segments
            seg_dist = dist_m * frac
            # Valley curvature: bends from North-West towards West-Southwest downstream
            bend = -65.0 * (frac ** 1.25)
            meander = math.sin(frac * math.pi * 3.0) * 8.0
            seg_azimuth = (base_azimuth + bend + meander) % 360.0

            d_lat, d_lon = meters_to_lat_lon_offsets(seg_dist, seg_azimuth, origin_lat)
            pt_lon = origin_lon + d_lon
            pt_lat = origin_lat + d_lat
            waypoints.append((pt_lon, pt_lat))

            # Valley width expands downstream
            valley_w = width_0 * (1.0 + (3.5 * frac))
            widths.append(valley_w)

        coords, wkt = generate_corridor_multipolygon(waypoints, widths)
        front_lon, front_lat = waypoints[-1]

        results.append(FloodTimeStepOutput(
            time_step_minutes=t_min,
            max_depth_m=round(h_current, 1),
            front_distance_km=round(dist_km, 2),
            front_latitude=round(front_lat, 5),
            front_longitude=round(front_lon, 5),
            polygon_coordinates=coords,
            wkt_geometry=wkt,
        ))

    return results
