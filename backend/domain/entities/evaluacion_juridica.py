from dataclasses import dataclass, field
from datetime import datetime, timezone

from backend.domain.value_objects.estado_evaluacion_juridica import (
    EstadoEvaluacionJuridica,
)


@dataclass(frozen=True, slots=True)
class EvaluacionJuridica:
    """Resultado estructurado de una consulta al servicio juridico."""

    proyecto_id: int
    estado: EstadoEvaluacionJuridica
    cumple: bool | None
    observaciones: tuple[str, ...]
    fuentes: tuple[str, ...]
    fecha_evaluacion: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
