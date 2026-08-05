"""
geo_utils.py
------------
Shared geometry helpers used by both demand_simulator.py and
batching_engine.py: the dark store location, the 4-vertical
(quadrant) split of the 10 sq km zone, and haversine distance.

Kept as a single small shared module so both files agree on:
  - what "north/south/east/west of the store" means,
  - how far apart two lat/lon points actually are.
"""

import math
from dataclasses import dataclass

EARTH_RADIUS_KM = 6371.0088

# The 4 verticals (quadrants), named N/S x E/W relative to the store.
VERTICALS = ["NE", "NW", "SE", "SW"]

# 10 sq km zone -> square of side sqrt(10) km, centered on the store.
ZONE_AREA_SQKM = 10.0
HALF_EXTENT_KM = math.sqrt(ZONE_AREA_SQKM) / 2  # ~1.581 km


@dataclass
class DarkStore:
    name: str
    lat: float
    lon: float


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in km."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def km_per_degree(lat: float):
    """Return (km_per_deg_lat, km_per_deg_lon) at a given latitude.
    Not geodesically exact, but fine for a synthetic simulation."""
    km_per_deg_lat = 111.0
    km_per_deg_lon = 111.0 * math.cos(math.radians(lat))
    return km_per_deg_lat, km_per_deg_lon


def classify_vertical(d_lat_km: float, d_lon_km: float) -> str:
    """N/S x E/W quadrant relative to the store, using the N-S/E-W
    lines through the store, as required by the spec."""
    ns = "N" if d_lat_km >= 0 else "S"
    ew = "E" if d_lon_km >= 0 else "W"
    return f"{ns}{ew}"  # one of VERTICALS


def clip_to_zone(d_lat_km: float, d_lon_km: float) -> tuple[float, float]:
    """Clip an offset so it stays inside the 10 sq km square zone."""
    d_lat_km = max(-HALF_EXTENT_KM, min(HALF_EXTENT_KM, d_lat_km))
    d_lon_km = max(-HALF_EXTENT_KM, min(HALF_EXTENT_KM, d_lon_km))
    return d_lat_km, d_lon_km
