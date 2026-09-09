"""Pruebas de la jerarquía de excepciones tipadas (src/exceptions.py)."""
from __future__ import annotations

import pytest

from src.exceptions import (
    AuthenticationError,
    ConfigError,
    ProjectError,
    ReporterError,
    SimulationError,
    ValidationError,
)


def test_all_exceptions_inherit_from_project_error():
    assert issubclass(ConfigError, ProjectError)
    assert issubclass(ValidationError, ProjectError)
    assert issubclass(SimulationError, ProjectError)
    assert issubclass(ReporterError, ProjectError)
    assert issubclass(AuthenticationError, ProjectError)


def test_project_error_base_has_default_error_code():
    exc = ProjectError("mensaje generico")
    assert exc.error_code == 1000
    assert exc.message == "mensaje generico"


def test_config_error_has_expected_code_and_message():
    exc = ConfigError("archivo no encontrado")
    assert exc.error_code == 1100
    assert "archivo no encontrado" in str(exc)
    assert "[DT-1100]" in str(exc)


def test_validation_error_has_expected_code():
    exc = ValidationError("campo fuera de rango")
    assert exc.error_code == 1200
    assert "[DT-1200]" in str(exc)


def test_simulation_error_has_expected_code():
    exc = SimulationError("replications debe ser >= 1")
    assert exc.error_code == 1300
    assert "[DT-1300]" in str(exc)


def test_reporter_error_has_expected_code_and_extra_attributes():
    exc = ReporterError("fallo al exportar PNG", artifact="dashboard_png", recoverable=True)
    assert exc.error_code == 1400
    assert exc.artifact == "dashboard_png"
    assert exc.recoverable is True
    assert "[DT-1400]" in str(exc)


def test_reporter_error_recoverable_defaults_to_true():
    exc = ReporterError("fallo grave", artifact="excel_report")
    assert exc.recoverable is True


def test_reporter_error_can_be_marked_non_recoverable():
    exc = ReporterError("fallo critico", artifact="excel_report", recoverable=False)
    assert exc.recoverable is False


def test_authentication_error_has_expected_code():
    exc = AuthenticationError("token expirado")
    assert exc.error_code == 1500
    assert "[DT-1500]" in str(exc)


def test_error_code_can_be_overridden_explicitly():
    exc = ConfigError("caso especial", error_code=1199)
    assert exc.error_code == 1199
    assert "[DT-1199]" in str(exc)


def test_exceptions_are_catchable_as_project_error_generic():
    """Un handler genérico que capture ProjectError debe atrapar cualquier subtipo."""
    with pytest.raises(ProjectError):
        raise SimulationError("fallo simulado")

    with pytest.raises(ProjectError):
        raise ReporterError("fallo simulado", artifact="dashboard_html")


def test_specific_exception_types_are_distinguishable():
    """Un handler específico NO debe atrapar un tipo distinto de excepción."""
    with pytest.raises(SimulationError):
        try:
            raise SimulationError("fallo de simulacion")
        except ConfigError:
            pytest.fail("ConfigError no deberia atrapar una SimulationError")