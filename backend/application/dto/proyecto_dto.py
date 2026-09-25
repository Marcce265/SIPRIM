from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from backend.domain.value_objects.estado_expediente import EstadoExpediente
from backend.domain.value_objects.estado_evaluacion_economica import (
    EstadoEvaluacionEconomica,
)
from backend.domain.value_objects.estado_evaluacion_juridica import (
    EstadoEvaluacionJuridica,
)
from backend.domain.value_objects.estado_proyecto import EstadoProyecto


class ProyectoCreate(BaseModel):
    """Contrato de entrada de HU1.1."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1, max_length=200)
    descripcion: str | None = Field(default=None, min_length=1, max_length=2000)
    ubicacion: str | None = Field(default=None, min_length=1, max_length=300)
    presupuesto: Decimal | None = Field(
        default=None, gt=0, max_digits=18, decimal_places=2
    )
    beneficiarios: int | None = Field(default=None, gt=0)
    tipo_proyecto: str | None = Field(default=None, min_length=1, max_length=150)

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("no puede estar vacio")
        return value

    @field_validator("descripcion", "ubicacion", "tipo_proyecto", mode="before")
    @classmethod
    def texto_vacio_es_dato_faltante(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class ProyectoResponse(BaseModel):
    """Representacion publica de un proyecto registrado."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None
    ubicacion: str | None
    presupuesto: Decimal | None
    beneficiarios: int | None
    tipo_proyecto: str | None
    estado: EstadoProyecto
    fecha_creacion: datetime

    @field_serializer("presupuesto", when_used="json")
    def serializar_presupuesto(self, value: Decimal | None) -> float | None:
        """Mantiene el contrato JSON como numero, aunque internamente use Decimal."""

        return float(value) if value is not None else None


class RegistrarProyectoResponse(BaseModel):
    mensaje: str
    proyecto: ProyectoResponse


class ValidacionProyectoResponse(BaseModel):
    estado: EstadoExpediente
    campos_faltantes: list[str]
    mensaje: str


class EvaluacionEconomicaResponse(BaseModel):
    proyecto_id: int
    presupuesto: Decimal
    beneficiarios: int
    costo_por_habitante: Decimal
    retorno_socioeconomico: Decimal | None
    estado_evaluacion: EstadoEvaluacionEconomica
    pendientes: list[str]

    @field_serializer(
        "presupuesto",
        "costo_por_habitante",
        "retorno_socioeconomico",
        when_used="json",
    )
    def serializar_importes(self, value: Decimal | None) -> float | None:
        return float(value) if value is not None else None


class EvaluacionJuridicaResponse(BaseModel):
    proyecto_id: int
    estado: EstadoEvaluacionJuridica
    cumple: bool | None
    observaciones: list[str]
    fuentes: list[str]
