from typing import Literal
from pydantic import BaseModel, Field


class DictamenIA(BaseModel):
    puntaje: float = Field(ge=0, le=100)
    viabilidad: Literal["ALTA", "MEDIA", "BAJA"]
    justificacion: str = Field(min_length=10)
    observaciones: list[str] = []
    recomendaciones: list[str] = []
