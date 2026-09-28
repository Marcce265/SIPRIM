from typing import Any

from backend.application.dto.evaluacion_ia_dto import DictamenIAResponse
from backend.domain.exceptions.proyecto_exceptions import (
    ExpedienteIncompletoError,
    ProyectoNoEncontradoError,
)
from backend.domain.ports.ia_service_port import IAServicePort
from backend.domain.ports.proyecto_repository_port import ProyectoRepositoryPort


class EvaluarProyectoIAUseCase:
    def __init__(
        self,
        proyecto_repository: ProyectoRepositoryPort,
        ia_service: IAServicePort,
    ) -> None:
        self._proyecto_repository = proyecto_repository
        self._ia_service = ia_service

    async def execute(self, proyecto_id: int) -> DictamenIAResponse:
        proyecto = self._proyecto_repository.obtener_por_id(proyecto_id)
        if proyecto is None:
            raise ProyectoNoEncontradoError(proyecto_id)

        campos_faltantes = proyecto.campos_faltantes()
        if campos_faltantes:
            raise ExpedienteIncompletoError(proyecto_id, campos_faltantes)

        ficha: dict[str, Any] = {
            "id": proyecto.id,
            "nombre": proyecto.nombre,
            "descripcion": proyecto.descripcion,
            "ubicacion": proyecto.ubicacion,
            "presupuesto": float(proyecto.presupuesto),
            "beneficiarios": proyecto.beneficiarios,
            "tipo_proyecto": proyecto.tipo_proyecto,
        }
        dictamen = await self._ia_service.generar_dictamen(ficha)
        return DictamenIAResponse.model_validate(dictamen)
