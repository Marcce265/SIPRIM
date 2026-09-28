from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class DictamenIA:
    """Resultado preliminar generado por el servicio de inteligencia artificial."""

    puntaje: float
    viabilidad: Literal["ALTA", "MEDIA", "BAJA"]
    justificacion: str
    observaciones: list[str]
    recomendaciones: list[str]
