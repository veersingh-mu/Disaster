"""Empirical breach parameter estimation formulas.

Implements published, peer-reviewed dam and glacial lake safety regressions:
1. Froehlich (2008) - Embankment Dam Breach Parameters and Their Uncertainties
2. Froehlich (1995a) - Peak Outflow from Breached Embankment Dams
3. MacDonald & Langridge-Monopolis (1984) - Breaching Characteristics of Dam Failures
4. Costa (1985) / USBR - Peak Discharge Envelope Models
"""

import math
from dataclasses import dataclass
from typing import Optional

from backend.app.models.enums import BreachType


@dataclass
class BreachParameters:
    """Estimated hydraulic and geometric parameters of a dam/lake breach."""
    peak_discharge_m3s: float
    breach_width_m: float
    breach_formation_time_hours: float
    breach_side_slope_z: float  # Horizontal : 1 Vertical (Z)
    breach_bottom_width_m: float
    volume_eroded_m3: Optional[float] = None
    hydrograph_time_to_peak_hours: float = 0.0
    method: str = "Froehlich (2008)"


def estimate_froehlich_breach(
    dam_height_m: float,
    dam_volume_m3: float,
    breach_type: BreachType = BreachType.STRUCTURAL,
) -> BreachParameters:
    """Estimate breach geometry, timing, and peak outflow using Froehlich (2008/1995).

    Parameters:
    - dam_height_m: Height of dam or moraine dam crest above river bed (m).
    - dam_volume_m3: Volume of water stored in the reservoir/lake (m³).
    - breach_type: 'structural' or 'landslide_glof' (affects overtopping/erosion factor Ko).

    Returns:
    - BreachParameters containing peak discharge, width, formation time, etc.
    """
    if dam_height_m <= 0:
        raise ValueError("dam_height_m must be strictly greater than 0.")
    if dam_volume_m3 <= 0:
        raise ValueError("dam_volume_m3 must be strictly greater than 0.")

    g = 9.80665

    # Ko factor: 1.3 for overtopping / GLOF rapid erosion; 1.0 for piping / structural
    k_o = 1.3 if breach_type == BreachType.LANDSLIDE_GLOF else 1.0

    # Side slope z (H:1V): 0.7 for rock/moraine/GLOF, 1.0 for earthfill
    z = 0.7 if breach_type == BreachType.LANDSLIDE_GLOF else 1.0

    # Average breach width B_avg = 0.27 * Ko * (V_w)^0.32 * (h_b)^0.04
    b_avg = 0.27 * k_o * (dam_volume_m3 ** 0.32) * (dam_height_m ** 0.04)
    # Ensure breach width is physically bounded
    b_avg = max(5.0, b_avg)

    # Bottom width W_b = B_avg - z * h_b
    w_b = max(1.0, b_avg - (z * dam_height_m))

    # Breach formation time t_f = 63.2 * sqrt(V_w / (g * h_b^2)) in seconds
    t_f_seconds = 63.2 * math.sqrt(dam_volume_m3 / (g * (dam_height_m ** 2)))
    # Reasonable physical bounds: between 6 minutes (0.1 hr) and 8 hours
    t_f_hours = max(0.1, min(8.0, t_f_seconds / 3600.0))

    # Peak outflow discharge Q_p = 0.607 * sqrt(Ko) * (V_w)^0.295 * (h_w)^1.24
    q_peak = 0.607 * math.sqrt(k_o) * (dam_volume_m3 ** 0.295) * (dam_height_m ** 1.24)
    q_peak = max(10.0, q_peak)

    # Time to peak hydrograph is typically ~20-30% of total formation time
    time_to_peak_h = t_f_hours * 0.25

    return BreachParameters(
        peak_discharge_m3s=round(q_peak, 2),
        breach_width_m=round(b_avg, 2),
        breach_formation_time_hours=round(t_f_hours, 3),
        breach_side_slope_z=z,
        breach_bottom_width_m=round(w_b, 2),
        hydrograph_time_to_peak_hours=round(time_to_peak_h, 3),
        method="Froehlich (2008)",
    )


def estimate_macdonald_breach(
    dam_height_m: float,
    dam_volume_m3: float,
) -> BreachParameters:
    """Estimate breach parameters using MacDonald & Langridge-Monopolis (1984)."""
    if dam_height_m <= 0 or dam_volume_m3 <= 0:
        raise ValueError("dam_height_m and dam_volume_m3 must be > 0.")

    # Volume of eroded material V_er = 0.0261 * (V_w * h_w)^0.77
    v_out_h = dam_volume_m3 * dam_height_m
    v_eroded = 0.0261 * (v_out_h ** 0.77)

    # Formation time t_f = 0.0179 * (V_er)^0.364 (hours)
    t_f_hours = max(0.1, 0.0179 * (v_eroded ** 0.364))

    # Average breach width estimate from volume eroded and height
    # V_er ~ B_avg * h_b * L (assuming crest length L ~ 3 * h_b)
    b_avg = max(5.0, v_eroded / (3.0 * (dam_height_m ** 2)))
    z = 0.5
    w_b = max(1.0, b_avg - (z * dam_height_m))

    # Peak flow from Costa envelope Q_p = 0.668 * (V_w * h_w)^0.46
    q_peak = 0.668 * (v_out_h ** 0.46)

    return BreachParameters(
        peak_discharge_m3s=round(q_peak, 2),
        breach_width_m=round(b_avg, 2),
        breach_formation_time_hours=round(t_f_hours, 3),
        breach_side_slope_z=z,
        breach_bottom_width_m=round(w_b, 2),
        volume_eroded_m3=round(v_eroded, 2),
        hydrograph_time_to_peak_hours=round(t_f_hours * 0.3, 3),
        method="MacDonald & Langridge-Monopolis (1984)",
    )


def calculate_breach_parameters(
    dam_height_m: float,
    dam_volume_m3: float,
    breach_type: BreachType = BreachType.STRUCTURAL,
    method: str = "froehlich",
) -> BreachParameters:
    """Unified entrypoint for breach parameter estimation."""
    if method.lower() == "macdonald":
        return estimate_macdonald_breach(dam_height_m, dam_volume_m3)
    return estimate_froehlich_breach(dam_height_m, dam_volume_m3, breach_type)
