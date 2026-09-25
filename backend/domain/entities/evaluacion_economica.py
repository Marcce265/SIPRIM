from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from backend.domain.value_objects.estado_evaluacion_economica import (
    EstadoEvaluacionEconomica,
)


@dataclass(frozen=True, slots=True)
class EvaluacionEconomica:
    """Resultado economico parcial asociado a un proyecto completo."""

    proyecto_id: int
    presupuesto: Decimal
    beneficiarios: int
    costo_por_habitante: Decimal
    retorno_socioeconomico: Decimal | None = None
    estado_evaluacion: EstadoEvaluacionEconomica = EstadoEvaluacionEconomica.PARCIAL
    pendientes: tuple[str, ...] = ("retorno_socioeconomico",)
    fecha_evaluacion: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @classmethod
    def calcular(
        cls, proyecto_id: int, presupuesto: Decimal, beneficiarios: int
    ) -> "EvaluacionEconomica":
        costo = (presupuesto / Decimal(beneficiarios)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return cls(
            proyecto_id=proyecto_id,
            presupuesto=presupuesto,
            beneficiarios=beneficiarios,
            costo_por_habitante=costo,
        )
