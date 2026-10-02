from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from backend.domain.value_objects.estado_evaluacion_economica import (
    EstadoEvaluacionEconomica,
)


@dataclass(frozen=True, slots=True)
class EvaluacionEconomica:
    """Resultado economico determinista y explicable del PMV1."""

    proyecto_id: int
    presupuesto: Decimal
    beneficiarios: int
    costo_por_habitante: Decimal
    score_0_100: Decimal
    costo_excelente: Decimal
    costo_inaceptable: Decimal
    version_criterios: int = 1
    formula: str = "presupuesto / beneficiarios"
    explicacion: str = ""
    version_algoritmo: str = "economic-cost-per-beneficiary-v1"
    retorno_socioeconomico: Decimal | None = None
    estado_evaluacion: EstadoEvaluacionEconomica = (
        EstadoEvaluacionEconomica.COMPLETADA
    )
    advertencias: tuple[str, ...] = (
        "No se calcula retorno socioeconomico sin datos de beneficios monetizados.",
    )
    fecha_evaluacion: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @classmethod
    def calcular(
        cls,
        proyecto_id: int,
        presupuesto: Decimal,
        beneficiarios: int,
        costo_excelente: Decimal = Decimal("200.00"),
        costo_inaceptable: Decimal = Decimal("500.00"),
        version_criterios: int = 1,
    ) -> "EvaluacionEconomica":
        if presupuesto <= 0:
            raise ValueError("presupuesto debe ser mayor a cero")
        if beneficiarios <= 0:
            raise ValueError("beneficiarios debe ser mayor a cero")
        if not Decimal("0") < costo_excelente < costo_inaceptable:
            raise ValueError(
                "los umbrales deben cumplir 0 < excelente < inaceptable"
            )

        costo_exacto = presupuesto / Decimal(beneficiarios)
        costo = costo_exacto.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if costo_exacto <= costo_excelente:
            score = Decimal("100")
        elif costo_exacto >= costo_inaceptable:
            score = Decimal("0")
        else:
            score = (
                Decimal("100")
                * (costo_inaceptable - costo_exacto)
                / (costo_inaceptable - costo_excelente)
            )
        score = score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        explicacion = (
            f"Costo por beneficiario = S/ {presupuesto} / {beneficiarios} = "
            f"S/ {costo}. Con umbral excelente S/ {costo_excelente} e "
            f"inaceptable S/ {costo_inaceptable}, la puntuacion es {score}/100. "
            "Indicador didactico: no mide retorno social ni viabilidad oficial."
        )
        return cls(
            proyecto_id=proyecto_id,
            presupuesto=presupuesto,
            beneficiarios=beneficiarios,
            costo_por_habitante=costo,
            score_0_100=score,
            costo_excelente=costo_excelente,
            costo_inaceptable=costo_inaceptable,
            version_criterios=version_criterios,
            explicacion=explicacion,
        )
