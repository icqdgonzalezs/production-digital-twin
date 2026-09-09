"""Cálculo de OEE (Overall Equipment Effectiveness) según ISO 22400.

OEE = Disponibilidad (A) x Rendimiento (P) x Calidad (Q)
"""
from __future__ import annotations

from typing import List

import numpy as np

from src.logging_config import get_logger
from src.models import ReplicationResult, StationConfig, StationMetrics

logger = get_logger(__name__)


def compute_station_oee(metrics: StationMetrics, nominal_cycle_time: float) -> StationMetrics:
    """Calcula Disponibilidad, Rendimiento, Calidad y OEE de una estación,
    a partir de los tiempos y conteos crudos registrados durante la simulación.

    Args:
        metrics: Métricas crudas de la estación (se modifican in-place).
        nominal_cycle_time: Tiempo de ciclo nominal, en minutos por unidad.

    Returns:
        El mismo objeto `metrics`, con los campos calculados actualizados.
    """
    total = metrics.total_time
    avail_time = total - metrics.downtime

    metrics.availability = avail_time / total if total > 0 else 0.0

    max_possible = avail_time / nominal_cycle_time if nominal_cycle_time > 0 else 0.0
    metrics.performance = (metrics.units_produced / max_possible) if max_possible > 0 else 0.0

    metrics.quality = (metrics.good_units / metrics.units_produced) if metrics.units_produced > 0 else 0.0

    metrics.oee = metrics.availability * metrics.performance * metrics.quality
    metrics.utilization = metrics.working_time / total if total > 0 else 0.0
    metrics.throughput = metrics.good_units / total if total > 0 else 0.0

    if total <= 0:
        logger.warning(
            "oee_computed_with_zero_total_time",
            extra={"station_id": metrics.station_id},
        )

    return metrics


def compute_replication_oee(results: List[ReplicationResult], stations_cfg: List[StationConfig]) -> None:
    """Aplica compute_station_oee a todas las estaciones de todas las réplicas,
    y calcula el OEE global (promedio) de cada réplica.

    Args:
        results: Lista de resultados de réplicas (se modifican in-place).
        stations_cfg: Configuración de estaciones, usada para obtener el
            tiempo de ciclo nominal de cada una.
    """
    for rep in results:
        for m in rep.station_metrics:
            cfg = next(s for s in stations_cfg if s.id == m.station_id)
            compute_station_oee(m, cfg.nominal_cycle_time)
        rep.overall_oee = float(np.mean([m.oee for m in rep.station_metrics]))

    logger.info(
        "oee_computed_for_all_replications",
        extra={"replication_count": len(results)},
    )