#!/usr/bin/env python3
"""CLI principal del simulador de línea de producción."""
import argparse
import os
from src.config_loader import load_config
from src.simulator import monte_carlo_simulation
from src.oee import compute_replication_oee
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
    compute_replication_oee(results, stations)

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
