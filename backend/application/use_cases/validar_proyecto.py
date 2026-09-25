from backend.application.dto.proyecto_dto import ValidacionProyectoResponse
from backend.domain.exceptions.proyecto_exceptions import ProyectoNoEncontradoError
from backend.domain.ports.proyecto_repository_port import ProyectoRepositoryPort
from backend.domain.value_objects.estado_expediente import EstadoExpediente


class ValidarProyectoUseCase:
    """Determina si el expediente contiene los datos exigidos para evaluarlo."""

    def __init__(self, repository: ProyectoRepositoryPort) -> None:
        self._repository = repository

    def execute(self, proyecto_id: int) -> ValidacionProyectoResponse:
        proyecto = self._repository.obtener_por_id(proyecto_id)
        if proyecto is None:
            raise ProyectoNoEncontradoError(proyecto_id)

        campos_faltantes = proyecto.campos_faltantes()
        if campos_faltantes:
            return ValidacionProyectoResponse(
                estado=EstadoExpediente.INCOMPLETO,
                campos_faltantes=campos_faltantes,
                mensaje="El expediente debe completarse antes de iniciar la evaluacion",
            )

        return ValidacionProyectoResponse(
            estado=EstadoExpediente.COMPLETO,
            campos_faltantes=[],
            mensaje="El expediente esta completo y puede iniciar la evaluacion",
        )
