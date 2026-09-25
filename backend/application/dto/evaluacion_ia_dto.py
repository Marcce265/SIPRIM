from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DictamenIAResponse(BaseModel):
    """Contrato publico y esquema estructurado para la evaluacion IA."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
        from_attributes=True,
    )

    puntaje: float = Field(ge=0, le=100, allow_inf_nan=False)
    viabilidad: Literal["ALTA", "MEDIA", "BAJA"]
    justificacion: str = Field(min_length=10)
    observaciones: list[str]
    recomendaciones: list[str]
