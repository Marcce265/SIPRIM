import pytest
from fastapi.testclient import TestClient

from backend.infrastructure.config.dependencies import get_proyecto_repository
from backend.main import create_app


@pytest.fixture
def client() -> TestClient:
    # Cada prueba recibe un repositorio temporal nuevo y determinista.
    get_proyecto_repository.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client
    get_proyecto_repository.cache_clear()


@pytest.fixture
def proyecto_valido() -> dict[str, object]:
    return {
        "nombre": "Mejoramiento de parque urbano",
        "descripcion": "Proyecto de recuperacion de espacio publico",
        "ubicacion": "El Tambo - Huancayo",
        "presupuesto": 2_500_000,
        "beneficiarios": 5_000,
        "tipo_proyecto": "Infraestructura urbana",
    }


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_registrar_y_consultar_proyecto(
    client: TestClient, proyecto_valido: dict[str, object]
) -> None:
    created = client.post("/api/v1/proyectos", json=proyecto_valido)

    assert created.status_code == 201
    body = created.json()
    assert body["mensaje"] == "Proyecto registrado correctamente"
    assert body["proyecto"]["id"] == 1
    assert body["proyecto"]["estado"] == "REGISTRADO"

    found = client.get("/api/v1/proyectos/1")
    assert found.status_code == 200
    assert found.json()["nombre"] == proyecto_valido["nombre"]
    assert found.json()["presupuesto"] == 2_500_000


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("nombre", "   "),
        ("presupuesto", 0),
        ("presupuesto", -1),
        ("beneficiarios", 0),
    ],
)
def test_rechaza_datos_invalidos(
    client: TestClient,
    proyecto_valido: dict[str, object],
    field: str,
    invalid_value: object,
) -> None:
    proyecto_valido[field] = invalid_value
    response = client.post("/api/v1/proyectos", json=proyecto_valido)
    assert response.status_code == 422


def test_registra_borrador_y_reporta_campos_faltantes(client: TestClient) -> None:
    created = client.post(
        "/api/v1/proyectos",
        json={"nombre": "Recuperacion de alameda", "descripcion": ""},
    )

    assert created.status_code == 201
    proyecto = created.json()["proyecto"]
    assert proyecto["estado"] == "BORRADOR"
    assert proyecto["descripcion"] is None

    validation = client.post("/api/v1/proyectos/1/validar")
    assert validation.status_code == 200
    assert validation.json() == {
        "estado": "INCOMPLETO",
        "campos_faltantes": [
            "descripcion",
            "ubicacion",
            "presupuesto",
            "beneficiarios",
            "tipo_proyecto",
        ],
        "mensaje": "El expediente debe completarse antes de iniciar la evaluacion",
    }


def test_valida_expediente_completo(
    client: TestClient, proyecto_valido: dict[str, object]
) -> None:
    client.post("/api/v1/proyectos", json=proyecto_valido)

    response = client.post("/api/v1/proyectos/1/validar")

    assert response.status_code == 200
    assert response.json() == {
        "estado": "COMPLETO",
        "campos_faltantes": [],
        "mensaje": "El expediente esta completo y puede iniciar la evaluacion",
    }


def test_validar_proyecto_inexistente_devuelve_404(client: TestClient) -> None:
    response = client.post("/api/v1/proyectos/999/validar")
    assert response.status_code == 404


def test_proyecto_inexistente_devuelve_404(client: TestClient) -> None:
    response = client.get("/api/v1/proyectos/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "No se encontro el proyecto con id 999"}
