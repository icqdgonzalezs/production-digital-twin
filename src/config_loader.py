"""Carga y valida la configuración YAML de la línea de producción."""
from __future__ import annotations

import os
from typing import Any, Dict

import yaml

from src.exceptions import ConfigError
from src.logging_config import get_logger
from src.models import StationConfig

logger = get_logger(__name__)

CAMPOS_REQUERIDOS = ["id", "name", "rate_upm", "cycle_time_std", "mtbf_min", "mttr_min", "quality_rate"]


def load_config(path: str = "config/line_config.yaml") -> Dict[str, Any]:
    """Carga y valida el archivo YAML de configuración de la línea.

    Args:
        path: Ruta relativa al archivo YAML de configuración.

    Returns:
        Diccionario con las claves 'stations' (List[StationConfig]),
        'buffers' (dict) y 'simulation' (dict).

    Raises:
        ConfigError: Si el archivo no existe, falta una sección requerida,
            o algún campo de estación tiene un valor fuera de rango.
    """
    if not os.path.exists(path):
        logger.error("config_file_not_found", extra={"path": path})
        raise ConfigError(f"No se encontro el archivo de configuracion: '{path}'")

    with open(path, "r") as f:
        config = yaml.safe_load(f)

    if not config or "stations" not in config:
        logger.error("config_missing_stations_key", extra={"path": path})
        raise ConfigError(f"El archivo '{path}' no contiene la clave 'stations'.")
    if not config["stations"]:
        logger.error("config_empty_stations", extra={"path": path})
        raise ConfigError("La configuracion debe tener al menos 1 estacion.")

    stations = [_parse_station(i, s) for i, s in enumerate(config["stations"])]

    if "simulation" not in config:
        logger.error("config_missing_simulation_section", extra={"path": path})
        raise ConfigError("Falta la seccion 'simulation' en la configuracion.")

    logger.info(
        "config_loaded_successfully",
        extra={"path": path, "station_count": len(stations)},
    )

    return {
        "stations": stations,
        "buffers": config.get("buffers", {"capacity": 50}),
        "simulation": config["simulation"],
    }


def _parse_station(index: int, raw: Dict[str, Any]) -> StationConfig:
    """Valida y construye un StationConfig a partir de un diccionario crudo.

    Args:
        index: Posición de la estación en la lista (0-based), usada solo
            para mensajes de error legibles.
        raw: Diccionario crudo leído del YAML para una estación.

    Raises:
        ConfigError: Si faltan campos requeridos o los valores están
            fuera de rango.
    """
    faltantes = [c for c in CAMPOS_REQUERIDOS if c not in raw]
    if faltantes:
        logger.error(
            "config_missing_required_fields",
            extra={"station_index": index + 1, "missing_fields": faltantes},
        )
        raise ConfigError(f"Estacion #{index + 1}: faltan campos requeridos: {faltantes}")

    if raw["rate_upm"] <= 0:
        logger.error(
            "config_invalid_rate_upm",
            extra={"station_id": raw["id"], "rate_upm": raw["rate_upm"]},
        )
        raise ConfigError(f"Estacion '{raw['id']}': rate_upm debe ser > 0 (recibido: {raw['rate_upm']})")

    if raw["mtbf_min"] <= 0:
        logger.error(
            "config_invalid_mtbf",
            extra={"station_id": raw["id"], "mtbf_min": raw["mtbf_min"]},
        )
        raise ConfigError(f"Estacion '{raw['id']}': mtbf_min debe ser > 0 (recibido: {raw['mtbf_min']})")

    if not (0 <= raw["quality_rate"] <= 1):
        logger.error(
            "config_invalid_quality_rate",
            extra={"station_id": raw["id"], "quality_rate": raw["quality_rate"]},
        )
        raise ConfigError(
            f"Estacion '{raw['id']}': quality_rate debe estar entre 0 y 1 (recibido: {raw['quality_rate']})"
        )

    return StationConfig(
        id=raw["id"],
        name=raw["name"],
        rate_upm=raw["rate_upm"],
        cycle_time_std=raw["cycle_time_std"],
        cycle_time_lsl=raw.get("cycle_time_lsl", 0.0),
        cycle_time_usl=raw.get("cycle_time_usl", float("inf")),
        mtbf_min=raw["mtbf_min"],
        mttr_min=raw["mttr_min"],
        quality_rate=raw["quality_rate"],
    )