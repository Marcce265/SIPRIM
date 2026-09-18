from backend.application.dto.proyecto_dto import ProyectoCreate
from backend.application.use_cases.registrar_proyecto import RegistrarProyectoUseCase
from backend.domain.value_objects.estado_proyecto import EstadoProyecto
from backend.infrastructure.output.repositories.in_memory_proyecto_repository import (
    InMemoryProyectoRepository,
)


def test_caso_de_uso_asigna_estado_e_id() -> None:
    use_case = RegistrarProyectoUseCase(InMemoryProyectoRepository())
    data = ProyectoCreate(
        nombre="Ciclovia metropolitana",
        descripcion="Conexion segura entre distritos",
        ubicacion="Huancayo",
        presupuesto=1_200_000,
        beneficiarios=15_000,
        tipo_proyecto="Movilidad urbana",
    )

    proyecto = use_case.execute(data)

    assert proyecto.id == 1
    assert proyecto.estado is EstadoProyecto.REGISTRADO

