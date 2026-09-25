from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.domain.entities.evaluacion_juridica import EvaluacionJuridica
from backend.domain.ports.evaluacion_juridica_repository_port import (
    EvaluacionJuridicaRepositoryPort,
)
from backend.domain.value_objects.estado_evaluacion_juridica import (
    EstadoEvaluacionJuridica,
)
from backend.infrastructure.output.database.models import EvaluacionJuridicaModel


class SQLAlchemyEvaluacionJuridicaRepository(EvaluacionJuridicaRepositoryPort):
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def guardar(self, evaluacion: EvaluacionJuridica) -> EvaluacionJuridica:
        with self._session_factory() as session:
            model = session.scalar(
                select(EvaluacionJuridicaModel).where(
                    EvaluacionJuridicaModel.proyecto_id == evaluacion.proyecto_id
                )
            )
            if model is None:
                model = EvaluacionJuridicaModel(proyecto_id=evaluacion.proyecto_id)
                session.add(model)

            model.estado = evaluacion.estado.value
            model.cumple = evaluacion.cumple
            model.observaciones = list(evaluacion.observaciones)
            model.fuentes = list(evaluacion.fuentes)
            model.fecha_evaluacion = evaluacion.fecha_evaluacion
            try:
                session.commit()
                session.refresh(model)
            except Exception:
                session.rollback()
                raise
            return self._to_entity(model)

    def obtener_por_proyecto(self, proyecto_id: int) -> EvaluacionJuridica | None:
        with self._session_factory() as session:
            model = session.scalar(
                select(EvaluacionJuridicaModel).where(
                    EvaluacionJuridicaModel.proyecto_id == proyecto_id
                )
            )
            return self._to_entity(model) if model is not None else None

    @staticmethod
    def _to_entity(model: EvaluacionJuridicaModel) -> EvaluacionJuridica:
        return EvaluacionJuridica(
            proyecto_id=model.proyecto_id,
            estado=EstadoEvaluacionJuridica(model.estado),
            cumple=model.cumple,
            observaciones=tuple(model.observaciones),
            fuentes=tuple(model.fuentes),
            fecha_evaluacion=model.fecha_evaluacion,
        )
