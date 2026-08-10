#!/usr/bin/env python3
"""CLI principal del simulador de línea de producción."""
import argparse
import os
import numpy as np
from src.config_loader import load_config
from src.simulator import monte_carlo_simulation
from src.reporter import generate_dashboard, generate_summary_png, generate_excel_report
from rich.console import Console

def main():
    parser = argparse.ArgumentParser(description='Production Line Simulator')
    parser.add_argument('--config', default='config/line_config.yaml')
    parser.add_argument('--replications', type=int)
    parser.add_argument('--no-dashboard', action='store_true')
    parser.add_argument('--no-png', action='store_true')
    parser.add_argument('--no-excel', action='store_true')
    args = parser.parse_args()

    console = Console()
    console.rule("[bold blue]Production Line Simulator[/bold blue]")
    console.print("Cargando configuración...", style="yellow")
    config = load_config(args.config)
    stations = config['stations']
    sim = config['simulation']
    reps = args.replications if args.replications else sim['replications']

    console.print(f"Estaciones: {len(stations)} | Réplicas: {reps}", style="cyan")

    # Ejecutar Monte Carlo
    results = monte_carlo_simulation(
        stations_cfg=stations,
        buffer_capacity=config['buffers']['capacity'],
        warmup=sim['warmup_min'],
        duration=sim['duration_min'],
        replications=reps,
        base_seed=sim['random_seed']
    )

    # Calcular OEE post-simulación
    for rep in results:
        for m in rep.station_metrics:
            cfg = next(s for s in stations if s.id == m.station_id)
            nominal = cfg.nominal_cycle_time
            total = m.total_time
            downtime = m.downtime
            avail_time = total - downtime
            m.availability = avail_time / total if total > 0 else 0
            max_possible = avail_time / nominal if nominal > 0 else 0
            m.performance = (m.units_produced / max_possible) if max_possible > 0 else 0
            m.quality = m.good_units / m.units_produced if m.units_produced > 0 else 0
            m.oee = m.availability * m.performance * m.quality
            m.utilization = m.working_time / total if total > 0 else 0
            m.throughput = m.good_units / total if total > 0 else 0
        rep.overall_oee = np.mean([m.oee for m in rep.station_metrics])

    console.print("[bold green]Simulación completada.[/bold green]")

    # Generar reportes
    os.makedirs("reports", exist_ok=True)
    if not args.no_dashboard:
        generate_dashboard(results, config)
    if not args.no_png:
        generate_summary_png(results, config)
    if not args.no_excel:
        generate_excel_report(results, config)

    console.print("[bold green]Reportes generados en la carpeta 'reports'.[/bold green]")

if __name__ == '__main__':
    main()
