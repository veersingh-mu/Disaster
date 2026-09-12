"""Geospatial coordinate extraction and utility functions."""

import re
from typing import Any, Tuple


def extract_point_coordinates(site_point: Any) -> Tuple[float, float]:
    """Safely extract (latitude, longitude) from various Point geometry representations."""
    raw_text = str(getattr(site_point, "data", site_point))
    # Match POINT(lon lat) or POINT (lon lat)
    match = re.search(r"POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)", raw_text, re.IGNORECASE)
    if match:
        lon = float(match.group(1))
        lat = float(match.group(2))
        return lat, lon

    # Fallback default coordinates (Himalayas)
    return 30.3833, 79.7333
