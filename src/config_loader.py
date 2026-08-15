"""Carga y valida la configuración YAML."""
import os
import yaml
from typing import Dict, Any
from src.models import StationConfig


class ConfigError(Exception):
    """Error de configuracion: archivo faltante, campo ausente o valor invalido."""
    pass


CAMPOS_REQUERIDOS = ['id', 'name', 'rate_upm', 'cycle_time_std', 'mtbf_min', 'mttr_min', 'quality_rate']


def load_config(path: str = "config/line_config.yaml") -> Dict[str, Any]:
    if not os.path.exists(path):
        raise ConfigError(f"No se encontro el archivo de configuracion: '{path}'")

    with open(path, 'r') as f:
        config = yaml.safe_load(f)

    if not config or 'stations' not in config:
        raise ConfigError(f"El archivo '{path}' no contiene la clave 'stations'.")
    if not config['stations']:
        raise ConfigError("La configuracion debe tener al menos 1 estacion.")

    stations = []
    for i, s in enumerate(config['stations']):
        faltantes = [c for c in CAMPOS_REQUERIDOS if c not in s]
        if faltantes:
            raise ConfigError(f"Estacion #{i+1}: faltan campos requeridos: {faltantes}")
        if s['rate_upm'] <= 0:
            raise ConfigError(f"Estacion '{s['id']}': rate_upm debe ser > 0 (recibido: {s['rate_upm']})")
        if s['mtbf_min'] <= 0:
            raise ConfigError(f"Estacion '{s['id']}': mtbf_min debe ser > 0 (recibido: {s['mtbf_min']})")
        if not (0 <= s['quality_rate'] <= 1):
            raise ConfigError(f"Estacion '{s['id']}': quality_rate debe estar entre 0 y 1 (recibido: {s['quality_rate']})")

        stations.append(StationConfig(
            id=s['id'], name=s['name'], rate_upm=s['rate_upm'],
            cycle_time_std=s['cycle_time_std'],
            cycle_time_lsl=s.get('cycle_time_lsl', 0.0),
            cycle_time_usl=s.get('cycle_time_usl', float('inf')),
            mtbf_min=s['mtbf_min'], mttr_min=s['mttr_min'],
            quality_rate=s['quality_rate']
        ))

    if 'simulation' not in config:
        raise ConfigError("Falta la seccion 'simulation' en la configuracion.")

    return {
        'stations': stations,
        'buffers': config.get('buffers', {'capacity': 50}),
        'simulation': config['simulation']
    }
