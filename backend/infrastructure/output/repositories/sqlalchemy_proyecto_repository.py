from collections.abc import Callable

from sqlalchemy.orm import Session

from backend.domain.entities.proyecto import Proyecto
from backend.domain.ports.proyecto_repository_port import ProyectoRepositoryPort
from backend.domain.value_objects.estado_proyecto import EstadoProyecto
from backend.infrastructure.output.database.models import ProyectoModel


class SQLAlchemyProyectoRepository(ProyectoRepositoryPort):
    """Adaptador PostgreSQL listo para activarse mediante configuracion."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def guardar(self, proyecto: Proyecto) -> Proyecto:
        with self._session_factory() as session:
            model = ProyectoModel(
                nombre=proyecto.nombre,
                descripcion=proyecto.descripcion,
                ubicacion=proyecto.ubicacion,
                presupuesto=proyecto.presupuesto,
                beneficiarios=proyecto.beneficiarios,
                tipo_proyecto=proyecto.tipo_proyecto,
                estado=proyecto.estado.value,
                fecha_creacion=proyecto.fecha_creacion,
            )
            try:
                session.add(model)
                session.commit()
                session.refresh(model)
            except Exception:
                session.rollback()
                raise
            return self._to_entity(model)

    def obtener_por_id(self, proyecto_id: int) -> Proyecto | None:
        with self._session_factory() as session:
            model = session.get(ProyectoModel, proyecto_id)
            return self._to_entity(model) if model is not None else None

    @staticmethod
    def _to_entity(model: ProyectoModel) -> Proyecto:
        return Proyecto(
            id=model.id,
            nombre=model.nombre,
            descripcion=model.descripcion,
            ubicacion=model.ubicacion,
            presupuesto=model.presupuesto,
            beneficiarios=model.beneficiarios,
            tipo_proyecto=model.tipo_proyecto,
            estado=EstadoProyecto(model.estado),
            fecha_creacion=model.fecha_creacion,
        )

