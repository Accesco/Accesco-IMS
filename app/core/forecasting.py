
from __future__ import annotations
import math
from typing import List, Tuple

def predict_holt_winters(
    series: List[float], 
    alpha: float = 0.4, 
    beta: float = 0.3, 
    forecast_steps: int = 1
) -> float:
    n = len(series)
    if n == 0:
        return 0.0
    if n == 1:
        return series[0]

    level = series[0]
    trend = series[1] - series[0]

    for i in range(1, n):
        last_level = level
        level = alpha * series[i] + (1 - alpha) * (level + trend)
        trend = beta * (level - last_level) + (1 - beta) * trend

    projection = level + (trend * forecast_steps)
    return max(0.0, round(projection, 3))


def calculate_optimal_batch_window(
    predicted_orders_per_min: float, 
    base_window_sec: int = 120
) -> Tuple[int, float]:
    if predicted_orders_per_min == 0:
        return base_window_sec, 1.0
        
    calculated_window = int(base_window_sec / math.sqrt(predicted_orders_per_min))
    bounded_window = max(45, min(180, calculated_window))
    
    expected_size = min(4.0, max(1.0, predicted_orders_per_min * (bounded_window / 60.0)))
    return bounded_window, round(expected_size, 2)