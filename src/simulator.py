"""Motor de simulación de eventos discretos con SimPy."""
import simpy
import random
import numpy as np
from typing import List
from src.models import StationConfig, StationMetrics, ReplicationResult
from src.bottleneck import detect_bottlenecks

def run_replication(env: simpy.Environment, stations_cfg: List[StationConfig],
                    buffer_capacity: int, warmup: float, duration: float,
                    seed: int) -> ReplicationResult:
    random.seed(seed)
    np.random.seed(seed)

    n_stations = len(stations_cfg)
    buffers = [simpy.Store(env, capacity=buffer_capacity) for _ in range(n_stations + 1)]

    # Colectores de métricas (uno por estación)
    collectors = [_StationMetricsCollector(cfg) for cfg in stations_cfg]

    # Arrancar procesos de estaciones
    for i, cfg in enumerate(stations_cfg):
        station = _Station(env, cfg, buffers[i], buffers[i+1], collectors[i], warmup, duration)
        env.process(station.run())

    # Fuente infinita de unidades
    env.process(_source(env, buffers[0]))

    # Ejecutar
    env.run(until=warmup + duration)

    # Construir resultados
    station_metrics = []
    for i, coll in enumerate(collectors):
        met = coll.finalize(env.now, warmup, duration)
        station_metrics.append(met)

    overall_oee = np.mean([m.oee for m in station_metrics])
    bottlenecks = detect_bottlenecks(station_metrics)
    return ReplicationResult(
        replication=0,
        overall_oee=overall_oee,
        station_metrics=station_metrics,
        bottlenecks=bottlenecks
    )

def monte_carlo_simulation(stations_cfg, buffer_capacity, warmup, duration,
                           replications, base_seed=42):
    results = []
    for rep in range(replications):
        seed = base_seed + rep
        env = simpy.Environment()
        rep_result = run_replication(env, stations_cfg, buffer_capacity,
                                     warmup, duration, seed)
        rep_result.replication = rep + 1
        results.append(rep_result)
    return results

class _StationMetricsCollector:
    def __init__(self, cfg: StationConfig):
        self.cfg = cfg
        self.working_time = 0.0
        self.downtime = 0.0
        self.blocked_time = 0.0
        self.starved_time = 0.0
        self.units_produced = 0
        self.good_units = 0
        self.cycle_times = []
        self.last_state_change = 0.0
        self.current_state = 'idle'
        self.processing_start = None

    def record_state(self, state: str, now: float):
        if state == self.current_state:
            return
        elapsed = now - self.last_state_change
        if self.current_state == 'working':
            self.working_time += elapsed
        elif self.current_state == 'down':
            self.downtime += elapsed
        elif self.current_state == 'blocked':
            self.blocked_time += elapsed
        elif self.current_state == 'starved':
            self.starved_time += elapsed
        self.current_state = state
        self.last_state_change = now

    def finalize(self, now, warmup, duration):
        # Forzar último cambio de estado
        self.record_state('idle', now)
        total_time = duration
        return StationMetrics(
            station_id=self.cfg.id,
            total_time=total_time,
            working_time=self.working_time,
            downtime=self.downtime,
            blocked_time=self.blocked_time,
            starved_time=self.starved_time,
            units_produced=self.units_produced,
            good_units=self.good_units,
            availability=0.0,  # se calculará luego
            performance=0.0,
            quality=0.0,
            oee=0.0,
            utilization=0.0,
            throughput=0.0,
            cycle_times=self.cycle_times
        )

class _Station:
    def __init__(self, env, cfg, in_buffer, out_buffer, collector, warmup, duration):
        self.env = env
        self.cfg = cfg
        self.in_buffer = in_buffer
        self.out_buffer = out_buffer
        self.collector = collector
        self.warmup = warmup
        self.duration = duration
        self.broken = False
        self.repaired = env.event()
        self._failure_process = env.process(self._failure_generator())

    def _failure_generator(self):
        while True:
            tbf = random.expovariate(1.0 / self.cfg.mtbf_min)
            yield self.env.timeout(tbf)
            self.broken = True
            self.repaired = self.env.event()
            if hasattr(self, '_current_processing') and self._current_processing.is_alive:
                self._current_processing.interrupt()
            ttr = random.expovariate(1.0 / self.cfg.mttr_min)
            yield self.env.timeout(ttr)
            self.broken = False
            self.repaired.succeed()

    def run(self):
        yield self.env.timeout(self.warmup)
        self.collector.last_state_change = self.env.now
        self.collector.current_state = 'idle'
        while True:
            self.collector.record_state('starved', self.env.now)
            unit = yield self.in_buffer.get()
            self.collector.record_state('working', self.env.now)
            self.collector.processing_start = self.env.now
            nominal = self.cfg.nominal_cycle_time
            std = self.cfg.cycle_time_std * nominal
            cycle = max(0.001, random.gauss(nominal, std))
            try:
                self._current_processing = self.env.process(self._process_unit(cycle))
                yield self._current_processing
            except simpy.Interrupt:
                # Unidad perdida por fallo
                self.collector.units_produced += 1
                self.collector.record_state('down', self.env.now)
                yield self.repaired
                self.collector.record_state('idle', self.env.now)
                continue
            processing_time = self.env.now - self.collector.processing_start
            self.collector.cycle_times.append(processing_time)
            if random.random() < self.cfg.quality_rate:
                self.collector.good_units += 1
                self.collector.units_produced += 1
                self.collector.record_state('blocked', self.env.now)
                yield self.out_buffer.put(unit)
                self.collector.record_state('idle', self.env.now)
            else:
                self.collector.units_produced += 1
                self.collector.record_state('idle', self.env.now)

    def _process_unit(self, cycle_time):
        yield self.env.timeout(cycle_time)

def _source(env, buffer):
    i = 0
    while True:
        yield buffer.put(f'unit_{i}')
        i += 1
