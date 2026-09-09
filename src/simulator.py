"""Motor de simulación de eventos discretos con SimPy."""
from __future__ import annotations

import random
from typing import List, Optional

import numpy as np
import simpy

from src.bottleneck import detect_bottlenecks
from src.exceptions import SimulationError
from src.logging_config import get_logger
from src.models import ReplicationResult, StationConfig, StationMetrics

logger = get_logger(__name__)


def run_replication(
    env: simpy.Environment,
    stations_cfg: List[StationConfig],
    buffer_capacity: int,
    warmup: float,
    duration: float,
    seed: int,
) -> ReplicationResult:
    """Ejecuta una única réplica de la simulación de la línea de producción.

    Args:
        env: Entorno SimPy sobre el que correr la réplica.
        stations_cfg: Configuración validada de cada estación de la línea.
        buffer_capacity: Capacidad finita de cada buffer entre estaciones.
        warmup: Minutos de calentamiento excluidos del cálculo de KPIs.
        duration: Duración simulada del turno, en minutos.
        seed: Semilla determinista para reproducibilidad de la réplica.

    Returns:
        Resultado de la réplica con métricas por estación y cuellos de botella.

    Raises:
        SimulationError: Si no hay estaciones configuradas.
    """
    if not stations_cfg:
        raise SimulationError("No se puede simular una linea sin estaciones configuradas.")

    random.seed(seed)
    np.random.seed(seed)

    n_stations = len(stations_cfg)
    buffers = [simpy.Store(env, capacity=buffer_capacity) for _ in range(n_stations + 1)]

    collectors = [_StationMetricsCollector(cfg) for cfg in stations_cfg]

    for i, cfg in enumerate(stations_cfg):
        station = _Station(env, cfg, buffers[i], buffers[i + 1], collectors[i], warmup, duration)
        env.process(station.run())

    env.process(_source(env, buffers[0]))
    env.process(_sink(env, buffers[-1]))

    env.run(until=warmup + duration)

    station_metrics = [coll.finalize(env.now, warmup, duration) for coll in collectors]

    overall_oee = float(np.mean([m.oee for m in station_metrics]))
    bottlenecks = detect_bottlenecks(station_metrics)

    return ReplicationResult(
        replication=0,
        overall_oee=overall_oee,
        station_metrics=station_metrics,
        bottlenecks=bottlenecks,
    )


def monte_carlo_simulation(
    stations_cfg: List[StationConfig],
    buffer_capacity: int,
    warmup: float,
    duration: float,
    replications: int,
    base_seed: int = 42,
) -> List[ReplicationResult]:
    """Ejecuta múltiples réplicas Monte Carlo de la simulación.

    Args:
        stations_cfg: Configuración validada de cada estación de la línea.
        buffer_capacity: Capacidad finita de cada buffer entre estaciones.
        warmup: Minutos de calentamiento excluidos del cálculo de KPIs.
        duration: Duración simulada del turno, en minutos.
        replications: Número de réplicas Monte Carlo a ejecutar.
        base_seed: Semilla base; cada réplica usa base_seed + índice.

    Returns:
        Lista de resultados, uno por réplica, con `replication` numerado desde 1.

    Raises:
        SimulationError: Si `replications` es menor a 1.
    """
    if replications < 1:
        raise SimulationError(f"El numero de replicaciones debe ser >= 1 (recibido: {replications})")

    logger.info(
        "monte_carlo_simulation_started",
        extra={
            "station_count": len(stations_cfg),
            "replications": replications,
            "base_seed": base_seed,
            "duration_min": duration,
            "warmup_min": warmup,
        },
    )

    results = []
    for rep in range(replications):
        seed = base_seed + rep
        env = simpy.Environment()
        rep_result = run_replication(env, stations_cfg, buffer_capacity, warmup, duration, seed)
        rep_result.replication = rep + 1
        results.append(rep_result)

    logger.info(
        "monte_carlo_simulation_completed",
        extra={"replications": replications, "overall_oee_mean": float(np.mean([r.overall_oee for r in results]))},
    )

    return results


class _StationMetricsCollector:
    """Acumula tiempos y conteos crudos de una estación durante una réplica."""

    def __init__(self, cfg: StationConfig) -> None:
        self.cfg = cfg
        self.working_time = 0.0
        self.downtime = 0.0
        self.blocked_time = 0.0
        self.starved_time = 0.0
        self.units_produced = 0
        self.good_units = 0
        self.cycle_times: List[float] = []
        self.last_state_change = 0.0
        self.current_state = "idle"
        self.processing_start: Optional[float] = None

    def record_state(self, state: str, now: float) -> None:
        if state == self.current_state:
            return
        elapsed = now - self.last_state_change
        if self.current_state == "working":
            self.working_time += elapsed
        elif self.current_state == "down":
            self.downtime += elapsed
        elif self.current_state == "blocked":
            self.blocked_time += elapsed
        elif self.current_state == "starved":
            self.starved_time += elapsed
        self.current_state = state
        self.last_state_change = now

    def finalize(self, now: float, warmup: float, duration: float) -> StationMetrics:
        self.record_state("idle", now)
        return StationMetrics(
            station_id=self.cfg.id,
            total_time=duration,
            working_time=self.working_time,
            downtime=self.downtime,
            blocked_time=self.blocked_time,
            starved_time=self.starved_time,
            units_produced=self.units_produced,
            good_units=self.good_units,
            availability=0.0,
            performance=0.0,
            quality=0.0,
            oee=0.0,
            utilization=0.0,
            throughput=0.0,
            cycle_times=self.cycle_times,
        )


class _Station:
    """Proceso SimPy que modela una estación de la línea: ciclo, fallas y buffers."""

    def __init__(
        self,
        env: simpy.Environment,
        cfg: StationConfig,
        in_buffer: simpy.Store,
        out_buffer: simpy.Store,
        collector: _StationMetricsCollector,
        warmup: float,
        duration: float,
    ) -> None:
        self.env = env
        self.cfg = cfg
        self.in_buffer = in_buffer
        self.out_buffer = out_buffer
        self.collector = collector
        self.warmup = warmup
        self.duration = duration
        self.broken = False
        self.repaired = env.event()
        # Estado explícito inicializado en __init__ (antes se creaba
        # dinámicamente vía `hasattr` dentro de `_failure_generator`).
        self._current_processing: Optional[simpy.Process] = None
        self._failure_process = env.process(self._failure_generator())

    def _failure_generator(self):
        while True:
            tbf = random.expovariate(1.0 / self.cfg.mtbf_min)
            yield self.env.timeout(tbf)
            self.broken = True
            self.repaired = self.env.event()
            if self._current_processing is not None and self._current_processing.is_alive:
                self._current_processing.interrupt()
            ttr = random.expovariate(1.0 / self.cfg.mttr_min)
            yield self.env.timeout(ttr)
            self.broken = False
            self.repaired.succeed()

    def run(self):
        yield self.env.timeout(self.warmup)
        self.collector.last_state_change = self.env.now
        self.collector.current_state = "idle"
        while True:
            self.collector.record_state("starved", self.env.now)
            unit = yield self.in_buffer.get()
            self.collector.record_state("working", self.env.now)
            self.collector.processing_start = self.env.now
            nominal = self.cfg.nominal_cycle_time
            std = self.cfg.cycle_time_std * nominal
            cycle = max(0.001, random.gauss(nominal, std))
            try:
                self._current_processing = self.env.process(self._process_unit(cycle))
                yield self._current_processing
            except simpy.Interrupt:
                self.collector.units_produced += 1
                self.collector.record_state("down", self.env.now)
                yield self.repaired
                self.collector.record_state("idle", self.env.now)
                continue
            processing_time = self.env.now - self.collector.processing_start
            self.collector.cycle_times.append(processing_time)
            if random.random() < self.cfg.quality_rate:
                self.collector.good_units += 1
                self.collector.units_produced += 1
                self.collector.record_state("blocked", self.env.now)
                yield self.out_buffer.put(unit)
                self.collector.record_state("idle", self.env.now)
            else:
                self.collector.units_produced += 1
                self.collector.record_state("idle", self.env.now)

    def _process_unit(self, cycle_time: float):
        yield self.env.timeout(cycle_time)


def _source(env: simpy.Environment, buffer: simpy.Store):
    """Fuente infinita: alimenta la primera estación con materia prima."""
    i = 0
    while True:
        yield buffer.put(f"unit_{i}")
        i += 1


def _sink(env: simpy.Environment, buffer: simpy.Store):
    """Sumidero: retira el producto terminado del último buffer,
    evitando que la última estación se bloquee esperando espacio."""
    while True:
        yield buffer.get()