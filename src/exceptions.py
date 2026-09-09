"""Jerarquía de excepciones tipadas para Production Digital Twin.

Regla del proyecto: nunca capturar `Exception` genérico en código de negocio.
Cada capa (config, simulación, reporte, validación, auth) lanza excepciones
específicas de esta jerarquía para que el llamador pueda distinguir el tipo
de fallo y reaccionar en consecuencia (reintentar, abortar, alertar).

Cada excepción lleva un `error_code` numérico estable, pensado para:
- correlacionar logs y alertas sin parsear texto libre;
- exponer códigos consistentes en una futura API HTTP (mapeo a status codes);
- documentación de soporte ("Error DT-1002: revisa tu archivo YAML").
"""
from __future__ import annotations


class ProjectError(Exception):
    """Excepción base de todo el dominio. Nunca se lanza directamente.

    Attributes:
        message: Descripción legible del error.
        error_code: Código numérico estable identificando el tipo de error.
    """

    error_code: int = 1000

    def __init__(self, message: str, *, error_code: int | None = None) -> None:
        self.message = message
        if error_code is not None:
            self.error_code = error_code
        super().__init__(f"[DT-{self.error_code}] {message}")


class ConfigError(ProjectError):
    """Error de configuración: archivo faltante, campo ausente o valor inválido."""

    error_code = 1100


class ValidationError(ProjectError):
    """Error de validación de datos de entrada (esquema, rangos, tipos).

    Se distingue de ConfigError porque ValidationError puede originarse en
    cualquier capa (p. ej. validación de payload de una futura API), no solo
    al cargar el YAML de configuración de línea.
    """

    error_code = 1200


class SimulationError(ProjectError):
    """Error durante la ejecución del motor de simulación (SimPy)."""

    error_code = 1300


class ReporterError(ProjectError):
    """Error al generar un artefacto de reporte (HTML, PNG, Excel o CSV).

    Attributes:
        artifact: Nombre del artefacto que falló (p. ej. "dashboard_png").
        recoverable: Si True, el llamador puede registrar y continuar sin
            abortar la generación de otros reportes.
    """

    error_code = 1400

    def __init__(
        self,
        message: str,
        *,
        artifact: str,
        recoverable: bool = True,
        error_code: int | None = None,
    ) -> None:
        self.artifact = artifact
        self.recoverable = recoverable
        super().__init__(message, error_code=error_code)


class AuthenticationError(ProjectError):
    """Error de autenticación/autorización.

    Reservada para la futura capa de API (Semana 2 del plan de auditoría):
    credenciales inválidas, token expirado, permisos insuficientes.
    """

    error_code = 1500