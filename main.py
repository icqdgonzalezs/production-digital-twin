#!/usr/bin/env python3
"""CLI principal del simulador de línea de producción."""
from __future__ import annotations

import argparse
import os

from rich.console import Console

from src.config_loader import load_config
from src.exceptions import ConfigError, ReporterError, SimulationError
from src.logging_config import get_logger
from src.oee import compute_replication_oee
from src.reporter import generate_dashboard, generate_excel_report, generate_summary_png
from src.simulator import monte_carlo_simulation

logger = get_logger("main")


def main() -> None:
    parser = argparse.ArgumentParser(description="Production Line Simulator")
    parser.add_argument("--config", default="config/line_config.yaml")
    parser.add_argument("--replications", type=int)
    parser.add_argument("--no-dashboard", action="store_true")
    parser.add_argument("--no-png", action="store_true")
    parser.add_argument("--no-excel", action="store_true")
    args = parser.parse_args()

    # rich.Console se usa exclusivamente para la experiencia visual de
    # terminal (colores, reglas). Los eventos que importan para auditoría,
    # debugging o monitoreo van siempre al logger estructurado.
    console = Console()
    console.rule("[bold blue]Production Line Simulator[/bold blue]")
    console.print("Cargando configuración...", style="yellow")

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        logger.error("cli_config_load_failed", extra={"config_path": args.config, "error": str(exc)})
        console.print(f"[bold red]Error de configuración:[/bold red] {exc}")
        raise SystemExit(1) from exc

    stations = config["stations"]
    sim = config["simulation"]
    reps = args.replications if args.replications else sim["replications"]

    console.print(f"Estaciones: {len(stations)} | Réplicas: {reps}", style="cyan")

    try:
        results = monte_carlo_simulation(
            stations_cfg=stations,
            buffer_capacity=config["buffers"]["capacity"],
            warmup=sim["warmup_min"],
            duration=sim["duration_min"],
            replications=reps,
            base_seed=sim["random_seed"],
        )
    except SimulationError as exc:
        logger.error("cli_simulation_failed", extra={"error": str(exc)})
        console.print(f"[bold red]Error de simulación:[/bold red] {exc}")
        raise SystemExit(1) from exc

    compute_replication_oee(results, stations)

    logger.info("cli_simulation_completed", extra={"replications": reps, "station_count": len(stations)})
    console.print("[bold green]Simulación completada.[/bold green]")

    os.makedirs("reports", exist_ok=True)
    if not args.no_dashboard:
        _run_report_step(console, "dashboard", lambda: generate_dashboard(results, config))
    if not args.no_png:
        _run_report_step(console, "summary_png", lambda: generate_summary_png(results, config))
    if not args.no_excel:
        _run_report_step(console, "excel_report", lambda: generate_excel_report(results, config))

    console.print("[bold green]Reportes generados en la carpeta 'reports'.[/bold green]")


def _run_report_step(console: Console, step_name: str, action) -> None:
    """Ejecuta un paso de generación de reportes, registrando fallos recuperables.

    Un fallo en un artefacto de reporte (p. ej. PNG por falta de kaleido)
    no debe impedir que se generen los demás artefactos.
    """
    try:
        action()
    except ReporterError as exc:
        if exc.recoverable:
            logger.warning(
                "cli_report_step_failed_continuing",
                extra={"step": step_name, "artifact": exc.artifact, "error": str(exc)},
            )
            console.print(f"[yellow]Aviso ({step_name}):[/yellow] {exc}")
        else:
            logger.error(
                "cli_report_step_failed_fatal",
                extra={"step": step_name, "artifact": exc.artifact, "error": str(exc)},
            )
            console.print(f"[bold red]Error fatal ({step_name}):[/bold red] {exc}")
            raise SystemExit(1) from exc


if __name__ == "__main__":
    main()