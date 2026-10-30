from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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

    @model_validator(mode="after")
    def validar_coherencia_del_dictamen(self) -> "DictamenIAResponse":
        esperada = "ALTA" if self.puntaje >= 70 else "MEDIA" if self.puntaje >= 40 else "BAJA"
        if self.viabilidad != esperada:
            raise ValueError("La viabilidad no corresponde al puntaje del dictamen")
        if any(not texto.strip() for texto in self.observaciones + self.recomendaciones):
            raise ValueError("Las observaciones y recomendaciones no pueden estar vacias")
        return self
