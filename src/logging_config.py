"""Configuración de logging estructurado (JSON) para Production Digital Twin.

Reemplaza todos los `print()` dispersos en el proyecto por un logger
único, con salida JSON parseable por sistemas de agregación (ELK, Loki, CloudWatch).

Uso:
    from src.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("simulation_started", extra={"replications": 100, "seed": 42})
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Formatea cada registro de log como una línea JSON.

    Campos incluidos siempre: timestamp (ISO 8601 UTC), level, logger, message.
    Campos adicionales pasados vía `extra={...}` se incluyen tal cual, bajo
    la clave `context`, para no colisionar con atributos internos de LogRecord.
    """

    RESERVED_ATTRS = frozenset(logging.LogRecord(
        name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
    ).__dict__.keys())

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # Cualquier atributo agregado vía `extra={...}` que no sea reservado
        # por el propio LogRecord se expone bajo "context".
        context = {
            key: value
            for key, value in record.__dict__.items()
            if key not in self.RESERVED_ATTRS and key != "message"
        }
        if context:
            payload["context"] = context

        return json.dumps(payload, default=str, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    """Devuelve un logger configurado con salida JSON a stdout.

    El nivel se controla vía la variable de entorno LOG_LEVEL
    (por defecto INFO). Idempotente: llamar varias veces con el mismo
    `name` no duplica handlers.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JSONFormatter())

    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False

    return logger