"""Detección de cuellos de botella e índices Cp/Cpk."""
import numpy as np
from typing import List
from src.models import BottleneckInfo, StationMetrics

def detect_bottlenecks(metrics: List[StationMetrics]) -> List[BottleneckInfo]:
    if not metrics:
        return []
    max_util = max(m.utilization for m in metrics)
    min_th = min(m.throughput for m in metrics)
    scores = []
    for m in metrics:
        util_norm = m.utilization / max_util if max_util > 0 else 0
        th_norm = min_th / m.throughput if m.throughput > 0 else 0
        composite = 0.5 * util_norm + 0.5 * th_norm
        scores.append(BottleneckInfo(
            station_id=m.station_id,
            utilization=m.utilization,
            throughput=m.throughput,
            composite_score=composite
        ))
    scores.sort(key=lambda x: x.composite_score, reverse=True)
    return scores

def compute_cp_cpk(cycle_times: List[float], lsl: float, usl: float):
    if len(cycle_times) < 2 or usl <= lsl:
        return None, None
    arr = np.array(cycle_times)
    mean = np.mean(arr)
    std = np.std(arr, ddof=1)
    if std == 0:
        return float('inf'), float('inf')
    cp = (usl - lsl) / (6 * std)
    cpk = min((usl - mean) / (3 * std), (mean - lsl) / (3 * std))
    return cp, cpk
