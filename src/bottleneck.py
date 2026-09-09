"""Detección de cuellos de botella e índices Cp/Cpk."""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np

from src.logging_config import get_logger
from src.models import BottleneckInfo, StationMetrics

logger = get_logger(__name__)


def detect_bottlenecks(metrics: List[StationMetrics]) -> List[BottleneckInfo]:
    """Calcula un score compuesto de cuello de botella por estación y las ordena.

    Args:
        metrics: Métricas de todas las estaciones de una réplica.

    Returns:
        Lista de BottleneckInfo ordenada de mayor a menor score compuesto.
        Lista vacía si `metrics` está vacío.
    """
    if not metrics:
        logger.warning("detect_bottlenecks_called_with_empty_metrics")
        return []

    max_util = max(m.utilization for m in metrics)
    min_th = min(m.throughput for m in metrics)
    scores = []
    for m in metrics:
        util_norm = m.utilization / max_util if max_util > 0 else 0
        th_norm = min_th / m.throughput if m.throughput > 0 else 0
        composite = 0.5 * util_norm + 0.5 * th_norm
        scores.append(
            BottleneckInfo(
                station_id=m.station_id,
                utilization=m.utilization,
                throughput=m.throughput,
                composite_score=composite,
            )
        )
    scores.sort(key=lambda x: x.composite_score, reverse=True)

    if scores:
        logger.info(
            "bottleneck_detected",
            extra={"station_id": scores[0].station_id, "composite_score": scores[0].composite_score},
        )

    return scores


def compute_cp_cpk(
    cycle_times: List[float], lsl: float, usl: float
) -> Tuple[Optional[float], Optional[float]]:
    """Calcula los índices de capacidad de proceso Cp y Cpk.

    Args:
        cycle_times: Tiempos de ciclo observados.
        lsl: Límite inferior de especificación.
        usl: Límite superior de especificación.

    Returns:
        Tupla (Cp, Cpk). Ambos son None si no hay datos suficientes
        (menos de 2 observaciones) o si los límites son inválidos (usl <= lsl).
    """
    if len(cycle_times) < 2 or usl <= lsl:
        return None, None

    arr = np.array(cycle_times)
    mean = np.mean(arr)
    std = np.std(arr, ddof=1)

    if std == 0:
        return float("inf"), float("inf")

    cp = (usl - lsl) / (6 * std)
    cpk = min((usl - mean) / (3 * std), (mean - lsl) / (3 * std))
    return cp, cpk