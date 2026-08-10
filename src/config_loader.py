"""Carga y valida la configuración YAML."""
import yaml
from typing import List, Dict, Any
from src.models import StationConfig

def load_config(path: str = "config/line_config.yaml") -> Dict[str, Any]:
    with open(path, 'r') as f:
        config = yaml.safe_load(f)
    stations = []
    for s in config['stations']:
        stations.append(StationConfig(
            id=s['id'],
            name=s['name'],
            rate_upm=s['rate_upm'],
            cycle_time_std=s['cycle_time_std'],
            cycle_time_lsl=s.get('cycle_time_lsl', 0.0),
            cycle_time_usl=s.get('cycle_time_usl', float('inf')),
            mtbf_min=s['mtbf_min'],
            mttr_min=s['mttr_min'],
            quality_rate=s['quality_rate']
        ))
    return {
        'stations': stations,
        'buffers': config.get('buffers', {'capacity': 50}),
        'simulation': config['simulation']
    }
