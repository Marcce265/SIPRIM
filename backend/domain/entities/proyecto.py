from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from backend.domain.exceptions.proyecto_exceptions import ProyectoInvalidoError
from backend.domain.value_objects.estado_proyecto import EstadoProyecto


@dataclass(slots=True)
class Proyecto:
    """Entidad raiz que protege las reglas esenciales de un proyecto urbano."""

    nombre: str
    descripcion: str | None = None
    ubicacion: str | None = None
    presupuesto: Decimal | None = None
    beneficiarios: int | None = None
    tipo_proyecto: str | None = None
    id: int | None = None
    estado: EstadoProyecto = EstadoProyecto.BORRADOR
    fecha_creacion: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if not self.nombre or not self.nombre.strip():
            raise ProyectoInvalidoError("nombre es obligatorio")
        self.nombre = self.nombre.strip()

        for campo in ("descripcion", "ubicacion", "tipo_proyecto"):
            valor = getattr(self, campo)
            if valor is not None:
                valor = valor.strip()
                setattr(self, campo, valor or None)

        if self.presupuesto is not None and self.presupuesto <= 0:
            raise ProyectoInvalidoError("presupuesto debe ser mayor a cero")
        if self.beneficiarios is not None and self.beneficiarios <= 0:
            raise ProyectoInvalidoError("beneficiarios debe ser mayor a cero")

        # El estado es derivado: un expediente incompleto se conserva como borrador.
        self.estado = (
            EstadoProyecto.REGISTRADO
            if not self.campos_faltantes()
            else EstadoProyecto.BORRADOR
        )

    def campos_faltantes(self) -> list[str]:
        """Lista ordenada de datos requeridos antes de iniciar una evaluacion."""

        campos_requeridos = {
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "ubicacion": self.ubicacion,
            "presupuesto": self.presupuesto,
            "beneficiarios": self.beneficiarios,
            "tipo_proyecto": self.tipo_proyecto,
        }
        return [campo for campo, valor in campos_requeridos.items() if valor is None]

