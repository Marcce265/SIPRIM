from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from backend.domain.exceptions.proyecto_exceptions import ProyectoInvalidoError
from backend.domain.value_objects.estado_proyecto import EstadoProyecto


@dataclass(slots=True)
class Proyecto:
    """Entidad raiz que protege las reglas esenciales de un proyecto urbano."""

    nombre: str
    descripcion: str
    ubicacion: str
    presupuesto: Decimal
    beneficiarios: int
    tipo_proyecto: str
    id: int | None = None
    estado: EstadoProyecto = EstadoProyecto.REGISTRADO
    fecha_creacion: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        campos_obligatorios = {
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "ubicacion": self.ubicacion,
            "tipo_proyecto": self.tipo_proyecto,
        }
        for campo, valor in campos_obligatorios.items():
            if not valor or not valor.strip():
                raise ProyectoInvalidoError(f"{campo} es obligatorio")
            setattr(self, campo, valor.strip())

        if self.presupuesto <= 0:
            raise ProyectoInvalidoError("presupuesto debe ser mayor a cero")
        if self.beneficiarios <= 0:
            raise ProyectoInvalidoError("beneficiarios debe ser mayor a cero")

