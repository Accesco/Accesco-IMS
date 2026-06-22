# app/core/geo_utils.py
from __future__ import annotations

import math
import itertools
from typing import List, Tuple, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.rider import Rider
    from app.models.order import Order
    from app.models.store import Store


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two coordinates in kilometers."""
    if None in (lat1, lon1, lat2, lon2):
        return float('inf')
    
    radius = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(d_lat / 2) ** 2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


def classify_zone_and_sla(distance_km: float) -> Tuple[str, int]:
    """Classifies delivery coordinates into concentric service zones (Section 04)."""
    if distance_km < 1.0:
        return "ZONE_A", 8
    elif distance_km < 2.0:
        return "ZONE_B", 12
    elif distance_km < 4.0:
        return "ZONE_C", 18
    else:
        return "ZONE_D", 25


def is_point_in_polygon(lat: float, lon: float, polygon_coords: List[List[float]]) -> bool:
    """
    Ray-casting containment algorithm checking if (lat, lon) is inside a GeoJSON polygon.
    Maps: x-axis -> longitude, y-axis -> latitude.
    """
    inside = False
    n = len(polygon_coords)
    p1x, p1y = polygon_coords[0][0], polygon_coords[0][1] # longitude (x), latitude (y)
    
    for i in range(n + 1):
        p2x, p2y = polygon_coords[i % n][0], polygon_coords[i % n][1]
        # Point's latitude (y) must lie between p1 and p2 latitude
        if lat > min(p1y, p2y):
            if lat <= max(p1y, p2y):
                # Point's longitude (x) must be to the left of the boundary edge
                if lon <= max(p1x, p2x):
                    if p1y != p2y:
                        xints = (lat - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or lon <= xints:
                        inside = not inside
        p1x, p1y = p2x, p2y
        
    return inside


def optimize_drops(orders: List[Dict[str, Any]], entry_gate: Tuple[float, float]) -> List[Dict[str, Any]]:
    """Brute-force Traveling Salesman Problem (TSP) solver for sequencing drops inside a community."""
    if not orders:
        return []
    
    best_sequence = []
    min_distance = float('inf')

    for seq in itertools.permutations(orders):
        current_dist = 0.0
        current_loc = entry_gate
        
        for order in seq:
            dist = haversine_distance(current_loc[0], current_loc[1], order["latitude"], order["longitude"])
            current_dist += dist
            current_loc = (order["latitude"], order["longitude"])
            
        if current_dist < min_distance:
            min_distance = current_dist
            best_sequence = list(seq)
            
    return best_sequence


def calculate_rae_score(
    rider: Rider,
    order: Order,
    store: Store,
    active_load_count: int,
    is_batch_compatible: bool,
    estimated_eta_min: float | None = None
) -> float:
    """Rider Assignment Engine (RAE) Multi-Factor Scoring Formula (Section 03)."""
    # 1. Proximity Score (35%)
    dist_rider_to_store = haversine_distance(rider.latitude, rider.longitude, store.latitude, store.longitude)
    dist_store_to_delivery = haversine_distance(store.latitude, store.longitude, order.latitude, order.longitude)
    total_distance = dist_rider_to_store + dist_store_to_delivery
    proximity_score = max(0.0, 1.0 - (total_distance / 10.0))

    # 2. Current Load Score (25%)
    load_score = max(0.0, (3.0 - active_load_count) / 3.0)

    # 3. ETA to Pickup Score (20%)
    if estimated_eta_min is None:
        estimated_eta_min = (dist_rider_to_store / 20.0) * 60.0
    eta_score = max(0.0, 1.0 - (estimated_eta_min / 30.0))

    # 4. Rider Performance Score (10%)
    performance_score = max(0.0, min(1.0, rider.performance_score))

    # 5. Batch Potential Score (10%)
    batch_potential_score = 1.0 if is_batch_compatible else 0.0

    final_score = (
        0.35 * proximity_score +
        0.25 * load_score +
        0.20 * eta_score +
        0.10 * performance_score +
        0.10 * batch_potential_score
    )
    return round(final_score, 4)