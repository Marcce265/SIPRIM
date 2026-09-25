from backend.application.dto.proyecto_dto import EvaluacionEconomicaResponse
from backend.domain.entities.evaluacion_economica import EvaluacionEconomica
from backend.domain.exceptions.proyecto_exceptions import (
    ExpedienteIncompletoError,
    ProyectoNoEncontradoError,
)
from backend.domain.ports.evaluacion_economica_repository_port import (
    EvaluacionEconomicaRepositoryPort,
)
from backend.domain.ports.proyecto_repository_port import ProyectoRepositoryPort


class EvaluarEconomiaProyectoUseCase:
    """Calcula y persiste los indicadores economicos definidos para el PMV1."""

    def __init__(
        self,
        proyecto_repository: ProyectoRepositoryPort,
        evaluacion_repository: EvaluacionEconomicaRepositoryPort,
    ) -> None:
        self._proyecto_repository = proyecto_repository
        self._evaluacion_repository = evaluacion_repository

    def execute(self, proyecto_id: int) -> EvaluacionEconomicaResponse:
        proyecto = self._proyecto_repository.obtener_por_id(proyecto_id)
        if proyecto is None:
            raise ProyectoNoEncontradoError(proyecto_id)

        campos_faltantes = proyecto.campos_faltantes()
        if campos_faltantes:
            raise ExpedienteIncompletoError(proyecto_id, campos_faltantes)

        # Tras validar el expediente, estos valores ya no pueden ser None.
        assert proyecto.id is not None
        assert proyecto.presupuesto is not None
        assert proyecto.beneficiarios is not None
        evaluacion = EvaluacionEconomica.calcular(
            proyecto_id=proyecto.id,
            presupuesto=proyecto.presupuesto,
            beneficiarios=proyecto.beneficiarios,
        )
        guardada = self._evaluacion_repository.guardar(evaluacion)
        return EvaluacionEconomicaResponse(
            proyecto_id=guardada.proyecto_id,
            presupuesto=guardada.presupuesto,
            beneficiarios=guardada.beneficiarios,
            costo_por_habitante=guardada.costo_por_habitante,
            retorno_socioeconomico=guardada.retorno_socioeconomico,
            estado_evaluacion=guardada.estado_evaluacion,
            pendientes=list(guardada.pendientes),
        )
