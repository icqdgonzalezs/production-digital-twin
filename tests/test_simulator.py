"""Pruebas unitarias del simulador de línea de producción."""
import pytest
import numpy as np

from src.models import StationConfig, StationMetrics, BottleneckInfo, ReplicationResult
from src.config_loader import load_config
from src.simulator import monte_carlo_simulation
from src.bottleneck import detect_bottlenecks, compute_cp_cpk
from src.oee import compute_station_oee, compute_replication_oee


# ---------- StationConfig ----------

def test_nominal_cycle_time():
    """rate_upm=60 unidades/min debe dar 1 unidad cada 1/60 min."""
    cfg = StationConfig(
        id="S01", name="Test", rate_upm=60.0, cycle_time_std=0.05,
        cycle_time_lsl=0.0, cycle_time_usl=1.0,
        mtbf_min=100, mttr_min=5, quality_rate=0.99
    )
    assert cfg.nominal_cycle_time == pytest.approx(1.0 / 60.0)


# ---------- config_loader ----------

def test_load_config_real_file():
    """Debe cargar el archivo real del repositorio sin errores."""
    config = load_config("config/line_config.yaml")
    assert "stations" in config
    assert len(config["stations"]) > 0
    assert isinstance(config["stations"][0], StationConfig)
    assert "buffers" in config
    assert "simulation" in config


# ---------- bottleneck.py ----------

def test_detect_bottlenecks_orders_by_composite_score():
    m1 = StationMetrics(
        station_id="A", total_time=100, working_time=90, downtime=5,
        blocked_time=0, starved_time=5, units_produced=90, good_units=88,
        availability=0.95, performance=0.9, quality=0.98, oee=0.83,
        utilization=0.95, throughput=0.88
    )
    m2 = StationMetrics(
        station_id="B", total_time=100, working_time=50, downtime=5,
        blocked_time=0, starved_time=45, units_produced=50, good_units=49,
        availability=0.95, performance=0.5, quality=0.98, oee=0.46,
        utilization=0.50, throughput=0.49
    )
    result = detect_bottlenecks([m1, m2])
    assert len(result) == 2
    assert result[0].station_id == "A"


def test_detect_bottlenecks_empty_list():
    assert detect_bottlenecks([]) == []


def test_compute_cp_cpk_known_values():
    cycle_times = [1, 2, 3, 4, 5]
    lsl, usl = 0.0, 10.0
    cp, cpk = compute_cp_cpk(cycle_times, lsl, usl)
    assert cp == pytest.approx(1.0541, abs=1e-3)
    assert cpk == pytest.approx(0.6325, abs=1e-3)


def test_compute_cp_cpk_insufficient_data():
    cp, cpk = compute_cp_cpk([1], lsl=0, usl=10)
    assert cp is None and cpk is None


def test_compute_cp_cpk_invalid_limits():
    cp, cpk = compute_cp_cpk([1, 2, 3], lsl=10, usl=5)
    assert cp is None and cpk is None


# ---------- oee.py ----------

def test_compute_station_oee_basic():
    m = StationMetrics(
        station_id="S01", total_time=100.0, working_time=80.0, downtime=10.0,
        blocked_time=5.0, starved_time=5.0, units_produced=100, good_units=95,
        availability=0, performance=0, quality=0, oee=0, utilization=0, throughput=0
    )
    nominal = 0.9
    result = compute_station_oee(m, nominal)

    assert result.availability == pytest.approx((100 - 10) / 100)
    assert result.quality == pytest.approx(95 / 100)
    assert 0 <= result.oee <= 1
    assert result.utilization == pytest.approx(80 / 100)


def test_compute_station_oee_zero_total_time():
    """No debe explotar (ZeroDivisionError) si total_time es 0."""
    m = StationMetrics(
        station_id="S01", total_time=0.0, working_time=0.0, downtime=0.0,
        blocked_time=0.0, starved_time=0.0, units_produced=0, good_units=0,
        availability=0, performance=0, quality=0, oee=0, utilization=0, throughput=0
    )
    result = compute_station_oee(m, nominal_cycle_time=1.0)
    assert result.availability == 0.0
    assert result.oee == 0.0


# ---------- simulator.py (test de integración, corto) ----------

def test_monte_carlo_simulation_end_to_end():
    """Simulación pequeña y rápida: valida que el motor completo corre sin errores
    y devuelve resultados con la forma esperada."""
    stations_cfg = [
        StationConfig(
            id="S01", name="Estación 1", rate_upm=60.0, cycle_time_std=0.05,
            cycle_time_lsl=0.0, cycle_time_usl=1.0,
            mtbf_min=200, mttr_min=5, quality_rate=0.99
        ),
        StationConfig(
            id="S02", name="Estación 2", rate_upm=55.0, cycle_time_std=0.05,
            cycle_time_lsl=0.0, cycle_time_usl=1.0,
            mtbf_min=200, mttr_min=5, quality_rate=0.99
        ),
    ]
    results = monte_carlo_simulation(
        stations_cfg=stations_cfg,
        buffer_capacity=10,
        warmup=0,
        duration=60,
        replications=2,
        base_seed=42
    )

    assert len(results) == 2
    for rep in results:
        assert len(rep.station_metrics) == 2
        for m in rep.station_metrics:
            assert m.total_time == pytest.approx(60)
            assert m.units_produced >= 0
            assert m.good_units <= m.units_produced

    compute_replication_oee(results, stations_cfg)
    for rep in results:
        assert 0 <= rep.overall_oee <= 1
        for m in rep.station_metrics:
            assert 0 <= m.oee <= 1
            assert 0 <= m.availability <= 1
            assert 0 <= m.quality <= 1


def test_monte_carlo_simulation_deterministic_seed():
    """Misma semilla base debe dar el mismo resultado (reproducibilidad)."""
    stations_cfg = [
        StationConfig(
            id="S01", name="Estación 1", rate_upm=60.0, cycle_time_std=0.05,
            cycle_time_lsl=0.0, cycle_time_usl=1.0,
            mtbf_min=200, mttr_min=5, quality_rate=0.99
        ),
    ]
    r1 = monte_carlo_simulation(stations_cfg, buffer_capacity=10, warmup=0,
                                 duration=60, replications=1, base_seed=99)
    r2 = monte_carlo_simulation(stations_cfg, buffer_capacity=10, warmup=0,
                                 duration=60, replications=1, base_seed=99)

    assert r1[0].station_metrics[0].units_produced == r2[0].station_metrics[0].units_produced
