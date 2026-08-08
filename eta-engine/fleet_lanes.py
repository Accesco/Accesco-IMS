"""
fleet_lanes.py
--------------
Static reference data for the truck/fleet TMS simulation: shipment
lanes (origin -> destination pairs) and the carrier fleet operating
them. This is the truck/freight equivalent of demand_simulator.py's
dark-store hotspots -- a small synthetic "world" to generate
realistic-looking telemetry against.

Per the blueprint (Accesco_Living_TMS_Implementation_Blueprint.md):
  - Assets are FTL/LTL trucks, not two-wheelers -- capacity is
    weight/volume bounded (18,000 kg / 60 CBM ceiling), not
    order-count bounded.
  - Carriers have a tracked identifier (stand-in for SCAC) and an
    efficiency/on-time score, referenced in the waterfall/tender logic
    and reused here as a feature for realistic per-carrier speed bias.

This is a synthetic placeholder network (no real warehouse/lane data
exists yet) -- swap LANES/CARRIERS for real facility coordinates and
your actual carrier roster once available.
"""

from dataclasses import dataclass


@dataclass
class Lane:
    lane_id: str
    origin_name: str
    destination_name: str
    distance_km: float
    # Free-flow speed range for this lane in clear conditions (km/h).
    # Highway-heavy lanes get a higher ceiling than mixed/urban lanes.
    free_flow_speed_min: float
    free_flow_speed_max: float


@dataclass
class Carrier:
    carrier_id: str
    name: str
    # Historical on-time performance score, 0-1 (matches the blueprint's
    # "historical on-time compliance" concept in the Carrier Master
    # Register). Used here as a realistic per-carrier speed/reliability
    # bias: a lower-scoring carrier tends to run a bit slower / more
    # variably, not just "unlucky. "
    on_time_score: float


# 6 synthetic regional lanes of varying length and road character.
LANES = [
    Lane("LANE-BLR-CHN", "Bengaluru DC", "Chennai Hub", 345.0, 55.0, 80.0),
    Lane("LANE-BLR-HYD", "Bengaluru DC", "Hyderabad Hub", 570.0, 55.0, 85.0),
    Lane("LANE-BLR-COK", "Bengaluru DC", "Kochi Hub", 460.0, 50.0, 75.0),
    Lane("LANE-BLR-PUN", "Bengaluru DC", "Pune Hub", 840.0, 55.0, 85.0),
    Lane("LANE-BLR-MAA", "Bengaluru DC", "Mangaluru Hub", 350.0, 45.0, 70.0),  # more ghats/curves -> lower ceiling
    Lane("LANE-BLR-VJA", "Bengaluru DC", "Vijayawada Hub", 430.0, 55.0, 80.0),
]

# 8 synthetic carriers with varying on-time performance.
CARRIERS = [
    Carrier("CARR-001", "Swift Freight Lines", 0.94),
    Carrier("CARR-002", "Highway Star Logistics", 0.89),
    Carrier("CARR-003", "Deccan Transport Co", 0.91),
    Carrier("CARR-004", "Coastal Carriers", 0.82),
    Carrier("CARR-005", "Trident Roadways", 0.87),
    Carrier("CARR-006", "Apex Cargo Movers", 0.95),
    Carrier("CARR-007", "Ghat Route Haulers", 0.78),
    Carrier("CARR-008", "Metro Line Transport", 0.90),
]

LANES_BY_ID = {l.lane_id: l for l in LANES}
CARRIERS_BY_ID = {c.carrier_id: c for c in CARRIERS}
