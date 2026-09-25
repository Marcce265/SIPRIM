from enum import Enum


class EstadoExpediente(str, Enum):
    """Resultado de validar si un expediente puede pasar a evaluacion."""

    COMPLETO = "COMPLETO"
    INCOMPLETO = "INCOMPLETO"
