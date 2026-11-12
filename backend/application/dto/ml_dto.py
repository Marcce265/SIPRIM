from __future__ import annotations

from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field


class InputMLProyectoDTO(BaseModel):
    monto_inversion: float = Field(..., gt=0, description="Monto total presupuestado en PEN")
    beneficiarios: int = Field(..., gt=0, description="Población beneficiaria directa")
    plazo_dias_programado: int = Field(default=180, gt=0, description="Plazo de ejecución en días calendario")
    tipo_proyecto: str = Field(default="Infraestructura urbana", description="Sector de inversión")
    zona_intervencion: str = Field(default="Urbana consolidada", description="Zona territorial (Urbana, Periurbana, Rural)")
    complejidad_tecnica: int = Field(default=2, ge=1, le=3, description="Nivel de complejidad (1: Baja, 2: Media, 3: Alta)")
    variacion_diseno_pct: float = Field(default=5.0, ge=0.0, le=100.0, description="Variación porcentual respecto a perfil")


class PrediccionSobrecostoDTO(BaseModel):
    probabilidad: float
    nivel_riesgo: Literal["BAJO", "MEDIO", "ALTO"]
    sobrecosto_estimado_pct: float
    factores_clave: list[str]


class PrediccionViabilidadPlazoDTO(BaseModel):
    clase_viabilidad: Literal["VIABLE", "RIESGO_MODERADO", "CRITICO"]
    retraso_estimado_dias: int
    probabilidad_desviacion: float
    alertas_programacion: list[str]


class DictamenMLResponseDTO(BaseModel):
    project_id: str
    expediente_code: str
    sobrecosto: PrediccionSobrecostoDTO
    viabilidad_plazo: PrediccionViabilidadPlazoDTO
    resumen_ejecutivo: str
    timestamp: str


class MetricasModelosMLDTO(BaseModel):
    dataset_size: int
    train_size: int
    test_size: int
    features: list[str]
    modelo_1_sobrecosto: dict[str, Any]
    modelo_2_viabilidad_plazo: dict[str, Any]
