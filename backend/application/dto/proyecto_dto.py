from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from backend.domain.value_objects.estado_proyecto import EstadoProyecto


class ProyectoCreate(BaseModel):
    """Contrato de entrada de HU1.1."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=200)
    descripcion: str = Field(min_length=1, max_length=2000)
    ubicacion: str = Field(min_length=1, max_length=300)
    presupuesto: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    beneficiarios: int = Field(gt=0)
    tipo_proyecto: str = Field(min_length=1, max_length=150)

    @field_validator("nombre", "descripcion", "ubicacion", "tipo_proyecto")
    @classmethod
    def no_permitir_texto_vacio(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("no puede estar vacio")
        return value


class ProyectoResponse(BaseModel):
    """Representacion publica de un proyecto registrado."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str
    ubicacion: str
    presupuesto: Decimal
    beneficiarios: int
    tipo_proyecto: str
    estado: EstadoProyecto
    fecha_creacion: datetime

    @field_serializer("presupuesto", when_used="json")
    def serializar_presupuesto(self, value: Decimal) -> float:
        """Mantiene el contrato JSON como numero, aunque internamente use Decimal."""

        return float(value)


class RegistrarProyectoResponse(BaseModel):
    mensaje: str
    proyecto: ProyectoResponse
