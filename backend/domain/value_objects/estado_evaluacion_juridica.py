from enum import Enum


class EstadoEvaluacionJuridica(str, Enum):
    """Estado explicito mientras la validacion normativa real no este conectada."""

    PENDIENTE_VALIDACION_NORMATIVA = "PENDIENTE_VALIDACION_NORMATIVA"
