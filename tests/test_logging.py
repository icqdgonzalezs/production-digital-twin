"""Pruebas del logging estructurado JSON (JSONFormatter + get_logger)."""
from __future__ import annotations

import io
import json
import logging

from src.logging_config import JSONFormatter, get_logger


def _capture_json_log(logger_name: str, log_fn_name: str, message: str, **extra) -> dict:
    """Ejecuta una llamada de logging y devuelve el JSON emitido, como dict."""
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    getattr(logger, log_fn_name)(message, extra=extra if extra else None)

    return json.loads(stream.getvalue().strip())


def test_log_output_is_valid_json():
    payload = _capture_json_log("test.valid_json", "info", "simulation_started")
    assert isinstance(payload, dict)


def test_log_output_has_required_fields():
    payload = _capture_json_log("test.required_fields", "info", "config_loaded_successfully")
    assert payload["level"] == "INFO"
    assert payload["logger"] == "test.required_fields"
    assert payload["message"] == "config_loaded_successfully"
    assert "timestamp" in payload


def test_extra_fields_are_nested_under_context():
    payload = _capture_json_log(
        "test.context_fields", "info", "config_loaded_successfully",
        path="config/line_config.yaml", station_count=4,
    )
    assert payload["context"]["path"] == "config/line_config.yaml"
    assert payload["context"]["station_count"] == 4


def test_warning_level_is_preserved():
    payload = _capture_json_log("test.warning_level", "warning", "oee_computed_with_zero_total_time")
    assert payload["level"] == "WARNING"


def test_error_level_is_preserved():
    payload = _capture_json_log("test.error_level", "error", "config_file_not_found")
    assert payload["level"] == "ERROR"


def test_get_logger_is_idempotent_no_duplicate_handlers():
    logger1 = get_logger("test.idempotent_unique")
    logger2 = get_logger("test.idempotent_unique")
    assert logger1 is logger2
    assert len(logger1.handlers) == 1


def test_get_logger_respects_log_level_env(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    logger = get_logger("test.env_level_unique")
    assert logger.level == logging.WARNING


def test_get_logger_defaults_to_info_level(monkeypatch):
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    logger = get_logger("test.default_level_unique")
    assert logger.level == logging.INFO


def test_no_context_key_when_no_extra_fields():
    payload = _capture_json_log("test.no_context", "info", "simulation_started")
    assert "context" not in payload