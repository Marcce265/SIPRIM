from backend.application.dto.proyecto_dto import EvaluacionJuridicaResponse
from backend.domain.exceptions.proyecto_exceptions import (
    ExpedienteIncompletoError,
    ProyectoNoEncontradoError,
)
from backend.domain.ports.evaluacion_juridica_port import EvaluacionJuridicaPort
from backend.domain.ports.evaluacion_juridica_repository_port import (
    EvaluacionJuridicaRepositoryPort,
)
from backend.domain.ports.proyecto_repository_port import ProyectoRepositoryPort


class EvaluarCumplimientoLegalUseCase:
    """Orquesta la evaluacion sin conocer RAG, Qdrant ni el transporte HTTP."""

    def __init__(
        self,
        proyecto_repository: ProyectoRepositoryPort,
        evaluador_juridico: EvaluacionJuridicaPort,
        evaluacion_repository: EvaluacionJuridicaRepositoryPort,
    ) -> None:
        self._proyecto_repository = proyecto_repository
        self._evaluador_juridico = evaluador_juridico
        self._evaluacion_repository = evaluacion_repository

    def execute(self, proyecto_id: int) -> EvaluacionJuridicaResponse:
        proyecto = self._proyecto_repository.obtener_por_id(proyecto_id)
        if proyecto is None:
            raise ProyectoNoEncontradoError(proyecto_id)

        campos_faltantes = proyecto.campos_faltantes()
        if campos_faltantes:
            raise ExpedienteIncompletoError(proyecto_id, campos_faltantes)

        evaluacion = self._evaluador_juridico.evaluar(proyecto)
        guardada = self._evaluacion_repository.guardar(evaluacion)
        return EvaluacionJuridicaResponse(
            proyecto_id=guardada.proyecto_id,
            estado=guardada.estado,
            cumple=guardada.cumple,
            observaciones=list(guardada.observaciones),
            fuentes=list(guardada.fuentes),
        )
