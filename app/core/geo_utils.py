from __future__ import annotations

import math
import itertools
import numpy as np
from scipy.optimize import linear_sum_assignment
from typing import List, Tuple, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.rider import Rider
    from app.models.order import Order
    from app.models.store import Store


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    if None in (lat1, lon1, lat2, lon2):
        return float('inf')
    radius = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


def classify_zone_and_sla(distance_km: float) -> Tuple[str, int]:
    if distance_km < 1.0:
        return "ZONE_A", 8
    elif distance_km < 2.0:
        return "ZONE_B", 12
    elif distance_km < 4.0:
        return "ZONE_C", 18
    else:
        return "ZONE_D", 25


def is_point_in_polygon(lat: float, lon: float, polygon_coords: List[List[float]]) -> bool:
    """Ray-casting containment algorithm with zero unbound variables [1]."""
    inside = False
    n = len(polygon_coords)
    p1x, p1y = polygon_coords[0][0], polygon_coords[0][1] # longitude (x), latitude (y)
    
    for i in range(n + 1):
        p2x, p2y = polygon_coords[i % n][0], polygon_coords[i % n][1]
        if lat > min(p1y, p2y):
            if lat <= max(p1y, p2y):
                if lon <= max(p1x, p2x):
                    if p1y != p2y:
                        xints = (lat - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or lon <= xints:
                            inside = not inside
                    elif p1x == p2x:
                        inside = not inside
        p1x, p1y = p2x, p2y
        
    return inside


def optimize_drops(orders: List[Dict[str, Any]], entry_gate: Tuple[float, float]) -> List[Dict[str, Any]]:
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


# ====================================================================
# PHASE 2 FUNCTION: INSTANT Dispatch RAE Matcher
# ====================================================================

def calculate_rae_score(
    rider: Rider,
    order: Order,
    store: Store,
    active_load_count: int,
    is_batch_compatible: bool,
    estimated_eta_min: float | None = None
) -> float:
    """Rider Assignment Engine (RAE) Multi-Factor Scoring Formula (Section 03) [4.1]."""
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


# ====================================================================
# PHASE 3 FUNCTION: OPTIMISATION MATRIX COST GENERATOR (Section 08) [11.1]
# ====================================================================

def calculate_assignment_cost(
    rider: Rider,
    store: Store,
    target_latitude: float,
    target_longitude: float,
    active_load_count: int,
    is_batch: bool,
    sla_time_left_sec: float,
    estimated_eta_min: float | None = None
) -> float:
    """
    Formulates a globally minimizable penalty value between a Rider and an Order/Batch (Section 08) [11.1].
    """
    # 1. Proximity Cost (30% Weight) [11.1]
    dist_rider_to_store = haversine_distance(rider.latitude, rider.longitude, store.latitude, store.longitude)
    dist_store_to_delivery = haversine_distance(store.latitude, store.longitude, target_latitude, target_longitude)
    total_dist = dist_rider_to_store + dist_store_to_delivery
    proximity_cost = min(10.0, total_dist)

    # 2. ETA Cost (25% Weight) [11.1]
    if estimated_eta_min is None:
        estimated_eta_min = (dist_rider_to_store / 20.0) * 60.0
    eta_cost = min(10.0, estimated_eta_min / 3.0)

    # 3. Current Rider Load Cost (25% Weight) [11.1]
    load_cost = (active_load_count / 3.0) * 10.0

    # 4. Performance Cost (10% Weight) [11.1]
    performance_cost = (1.0 - max(0.0, min(1.0, rider.performance_score))) * 10.0

    # 5. Batching & Status Bonuses (10% Weight total) [11.1]
    batch_bonus = 1.5 if is_batch else 0.0
    returning_bonus = 1.0 if rider.status == "RETURNING" else 0.0
    status_bonus = batch_bonus + returning_bonus

    # 6. Battery Penalty
    battery_penalty = (1.0 - (rider.battery_level / 100.0)) * 2.0

    # 7. SLA Urgent Penalty (Escalation Factor)
    sla_risk_factor = max(0.0, (1200.0 - sla_time_left_sec) / 120.0) if sla_time_left_sec < 1200 else 0.0

    total_cost = (
        0.30 * proximity_cost +
        0.25 * eta_cost +
        0.25 * load_cost +
        0.10 * performance_cost +
        battery_penalty -
        status_bonus -
        sla_risk_factor
    )
    
    return max(0.1, round(total_cost, 4))


def solve_hungarian_exact(cost_matrix: np.ndarray) -> List[Tuple[int, int]]:
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    return list(zip(row_ind, col_ind))


def solve_auction_approximate(
    cost_matrix: np.ndarray, 
    epsilon: float = 0.01, 
    max_iterations: int = 1000
) -> List[Tuple[int, int]]:
    num_bidders, num_items = cost_matrix.shape
    max_val = np.max(cost_matrix) + 1.0
    benefits = max_val - cost_matrix
    
    prices = np.zeros(num_items)
    assignments: Dict[int, int] = {}
    bidder_assigned = np.full(num_bidders, -1)
    
    iteration = 0
    while len(assignments) < min(num_bidders, num_items) and iteration < max_iterations:
        iteration += 1
        for bidder in range(num_bidders):
            if bidder_assigned[bidder] != -1:
                continue
                
            value = benefits[bidder, :] - prices
            best_item = int(np.argmax(value))
            v1 = value[best_item]
            
            # Find second best value
            tmp_val = value.copy()
            tmp_val[best_item] = -float('inf')
            v2 = tmp_val.max()
            
            bid = (v1 - v2) + epsilon
            prices[best_item] += bid
            
            if best_item in assignments:
                prev_bidder = assignments[best_item]
                bidder_assigned[prev_bidder] = -1
                
            assignments[best_item] = bidder
            bidder_assigned[bidder] = best_item
            
    matches = []
    for bidder, item in enumerate(bidder_assigned):
        if item != -1:
            matches.append((bidder, item))
    return matches