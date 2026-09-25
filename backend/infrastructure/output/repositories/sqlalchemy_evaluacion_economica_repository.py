from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.domain.entities.evaluacion_economica import EvaluacionEconomica
from backend.domain.ports.evaluacion_economica_repository_port import (
    EvaluacionEconomicaRepositoryPort,
)
from backend.domain.value_objects.estado_evaluacion_economica import (
    EstadoEvaluacionEconomica,
)
from backend.infrastructure.output.database.models import EvaluacionEconomicaModel


class SQLAlchemyEvaluacionEconomicaRepository(EvaluacionEconomicaRepositoryPort):
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def guardar(self, evaluacion: EvaluacionEconomica) -> EvaluacionEconomica:
        with self._session_factory() as session:
            model = session.scalar(
                select(EvaluacionEconomicaModel).where(
                    EvaluacionEconomicaModel.proyecto_id == evaluacion.proyecto_id
                )
            )
            if model is None:
                model = EvaluacionEconomicaModel(proyecto_id=evaluacion.proyecto_id)
                session.add(model)

            model.presupuesto = evaluacion.presupuesto
            model.beneficiarios = evaluacion.beneficiarios
            model.costo_por_habitante = evaluacion.costo_por_habitante
            model.retorno_socioeconomico = evaluacion.retorno_socioeconomico
            model.estado_evaluacion = evaluacion.estado_evaluacion.value
            model.pendientes = list(evaluacion.pendientes)
            model.fecha_evaluacion = evaluacion.fecha_evaluacion
            try:
                session.commit()
                session.refresh(model)
            except Exception:
                session.rollback()
                raise
            return self._to_entity(model)

    def obtener_por_proyecto(
        self, proyecto_id: int
    ) -> EvaluacionEconomica | None:
        with self._session_factory() as session:
            model = session.scalar(
                select(EvaluacionEconomicaModel).where(
                    EvaluacionEconomicaModel.proyecto_id == proyecto_id
                )
            )
            return self._to_entity(model) if model is not None else None

    @staticmethod
    def _to_entity(model: EvaluacionEconomicaModel) -> EvaluacionEconomica:
        return EvaluacionEconomica(
            proyecto_id=model.proyecto_id,
            presupuesto=model.presupuesto,
            beneficiarios=model.beneficiarios,
            costo_por_habitante=model.costo_por_habitante,
            retorno_socioeconomico=model.retorno_socioeconomico,
            estado_evaluacion=EstadoEvaluacionEconomica(model.estado_evaluacion),
            pendientes=tuple(model.pendientes),
            fecha_evaluacion=model.fecha_evaluacion,
        )
