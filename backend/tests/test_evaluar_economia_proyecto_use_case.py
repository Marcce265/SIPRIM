from decimal import Decimal

from backend.application.dto.proyecto_dto import ProyectoCreate
from backend.application.use_cases.evaluar_economia_proyecto import (
    EvaluarEconomiaProyectoUseCase,
)
from backend.application.use_cases.registrar_proyecto import RegistrarProyectoUseCase
from backend.infrastructure.output.repositories.in_memory_evaluacion_economica_repository import (
    InMemoryEvaluacionEconomicaRepository,
)
from backend.infrastructure.output.repositories.in_memory_proyecto_repository import (
    InMemoryProyectoRepository,
)


def test_calcula_redondea_y_persiste_costo_por_habitante() -> None:
    proyectos = InMemoryProyectoRepository()
    evaluaciones = InMemoryEvaluacionEconomicaRepository()
    proyecto = RegistrarProyectoUseCase(proyectos).execute(
        ProyectoCreate(
            nombre="Parque",
            descripcion="Recuperacion urbana",
            ubicacion="Huancayo",
            presupuesto=Decimal("1000"),
            beneficiarios=3,
            tipo_proyecto="Infraestructura urbana",
        )
    )
    use_case = EvaluarEconomiaProyectoUseCase(proyectos, evaluaciones)

    resultado = use_case.execute(proyecto.id or 0)

    assert resultado.costo_por_habitante == Decimal("333.33")
    assert resultado.estado_evaluacion.value == "PARCIAL"
    assert resultado.retorno_socioeconomico is None
    assert evaluaciones.obtener_por_proyecto(proyecto.id or 0) is not None
