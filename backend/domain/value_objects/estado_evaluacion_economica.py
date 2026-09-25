from enum import Enum


class EstadoEvaluacionEconomica(str, Enum):
    """Estado del calculo economico disponible en el PMV1."""

    PARCIAL = "PARCIAL"
