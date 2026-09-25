from backend.application.dto.proyecto_dto import ProyectoCreate
from backend.application.use_cases.evaluar_cumplimiento_legal import (
    EvaluarCumplimientoLegalUseCase,
)
from backend.application.use_cases.registrar_proyecto import RegistrarProyectoUseCase
from backend.infrastructure.output.legal.evaluacion_juridica_provisional_adapter import (
    EvaluacionJuridicaProvisionalAdapter,
)
from backend.infrastructure.output.repositories.in_memory_evaluacion_juridica_repository import (
    InMemoryEvaluacionJuridicaRepository,
)
from backend.infrastructure.output.repositories.in_memory_proyecto_repository import (
    InMemoryProyectoRepository,
)


def test_invoca_puerto_juridico_y_persiste_resultado() -> None:
    proyectos = InMemoryProyectoRepository()
    evaluaciones = InMemoryEvaluacionJuridicaRepository()
    proyecto = RegistrarProyectoUseCase(proyectos).execute(
        ProyectoCreate(
            nombre="Parque",
            descripcion="Recuperacion urbana",
            ubicacion="Huancayo",
            presupuesto=1000,
            beneficiarios=10,
            tipo_proyecto="Infraestructura urbana",
        )
    )
    use_case = EvaluarCumplimientoLegalUseCase(
        proyectos,
        EvaluacionJuridicaProvisionalAdapter(),
        evaluaciones,
    )

    resultado = use_case.execute(proyecto.id or 0)

    assert resultado.estado.value == "PENDIENTE_VALIDACION_NORMATIVA"
    assert resultado.cumple is None
    assert resultado.fuentes == []
    assert evaluaciones.obtener_por_proyecto(proyecto.id or 0) is not None
