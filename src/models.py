"""Dataclasses para configuración, resultados y cuellos de botella."""
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class StationConfig:
    id: str
    name: str
    rate_upm: float
    cycle_time_std: float
    cycle_time_lsl: float
    cycle_time_usl: float
    mtbf_min: float
    mttr_min: float
    quality_rate: float

    @property
    def nominal_cycle_time(self) -> float:
        """minutos por unidad"""
        return 1.0 / self.rate_upm

@dataclass
class StationMetrics:
    station_id: str
    total_time: float
    working_time: float
    downtime: float
    blocked_time: float
    starved_time: float
    units_produced: int
    good_units: int
    availability: float
    performance: float
    quality: float
    oee: float
    utilization: float
    throughput: float
    cycle_times: List[float] = field(default_factory=list)

@dataclass
class BottleneckInfo:
    station_id: str
    utilization: float
    throughput: float
    composite_score: float

@dataclass
class ReplicationResult:
    replication: int
    overall_oee: float
    station_metrics: List[StationMetrics]
    bottlenecks: List[BottleneckInfo]
