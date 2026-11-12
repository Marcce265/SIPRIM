from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4


NivelRiesgoSobrecosto = Literal["BAJO", "MEDIO", "ALTO"]
ClaseViabilidadPlazo = Literal["VIABLE", "RIESGO_MODERADO", "CRITICO"]


@dataclass(frozen=True)
class PrediccionSobrecosto:
    probabilidad: float
    nivel_riesgo: NivelRiesgoSobrecosto
    sobrecosto_estimado_pct: float
    factores_clave: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PrediccionViabilidadPlazo:
    clase_viabilidad: ClaseViabilidadPlazo
    retraso_estimado_dias: int
    probabilidad_desviacion: float
    alertas_programacion: list[str] = field(default_factory=list)


@dataclass
class DictamenMLUnificado:
    id: UUID
    project_id: UUID
    expediente_code: str
    sobrecosto: PrediccionSobrecosto
    viabilidad_plazo: PrediccionViabilidadPlazo
    resumen_ejecutivo: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def crear(
        cls,
        project_id: UUID,
        expediente_code: str,
        sobrecosto: PrediccionSobrecosto,
        viabilidad_plazo: PrediccionViabilidadPlazo,
        resumen_ejecutivo: str,
    ) -> DictamenMLUnificado:
        return cls(
            id=uuid4(),
            project_id=project_id,
            expediente_code=expediente_code,
            sobrecosto=sobrecosto,
            viabilidad_plazo=viabilidad_plazo,
            resumen_ejecutivo=resumen_ejecutivo,
        )
