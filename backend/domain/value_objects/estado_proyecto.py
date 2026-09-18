from enum import Enum


class EstadoProyecto(str, Enum):
    """Estados validos del ciclo de vida del proyecto."""

    REGISTRADO = "REGISTRADO"

