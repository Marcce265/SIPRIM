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
    assert resultado.costo_por_beneficiario == Decimal("333.33")
    assert resultado.score_0_100 == Decimal("55.56")
    assert resultado.estado_evaluacion.value == "COMPLETADA"
    assert resultado.retorno_socioeconomico is None
    assert "no mide retorno social" in resultado.explicacion
    assert evaluaciones.obtener_por_proyecto(proyecto.id or 0) is not None


def test_puntuacion_economica_respeta_los_umbrales_documentados() -> None:
    from backend.domain.entities.evaluacion_economica import EvaluacionEconomica

    excelente = EvaluacionEconomica.calcular(
        proyecto_id=1, presupuesto=Decimal("120000"), beneficiarios=600
    )
    intermedio = EvaluacionEconomica.calcular(
        proyecto_id=2, presupuesto=Decimal("90000"), beneficiarios=300
    )

    assert excelente.costo_por_habitante == Decimal("200.00")
    assert excelente.score_0_100 == Decimal("100.00")
    assert intermedio.costo_por_habitante == Decimal("300.00")
    assert intermedio.score_0_100 == Decimal("66.67")


def test_rechaza_umbrales_economicos_invertidos() -> None:
    import pytest
    from backend.domain.entities.evaluacion_economica import EvaluacionEconomica

    with pytest.raises(ValueError, match="0 < excelente < inaceptable"):
        EvaluacionEconomica.calcular(
            proyecto_id=1,
            presupuesto=Decimal("1000"),
            beneficiarios=10,
            costo_excelente=Decimal("500"),
            costo_inaceptable=Decimal("200"),
        )
