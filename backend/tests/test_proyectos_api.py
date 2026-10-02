import pytest
from fastapi.testclient import TestClient

from backend.infrastructure.config.dependencies import (
    get_evaluacion_economica_repository,
    get_evaluacion_juridica_repository,
    get_evaluador_juridico,
    get_proyecto_repository,
)
from backend.main import create_app


@pytest.fixture
def client() -> TestClient:
    # Cada prueba recibe un repositorio temporal nuevo y determinista.
    get_proyecto_repository.cache_clear()
    get_evaluacion_economica_repository.cache_clear()
    get_evaluacion_juridica_repository.cache_clear()
    get_evaluador_juridico.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client
    get_proyecto_repository.cache_clear()
    get_evaluacion_economica_repository.cache_clear()
    get_evaluacion_juridica_repository.cache_clear()
    get_evaluador_juridico.cache_clear()


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
    assert body["proyecto"]["codigo"].startswith("PRY-")
    assert body["proyecto"]["version_numero"] == 1
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
    assert proyecto["codigo"].startswith("PRY-")
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


def test_normaliza_codigo_proporcionado(
    client: TestClient, proyecto_valido: dict[str, object]
) -> None:
    proyecto_valido["codigo"] = "pry-parque-01"

    response = client.post("/api/v1/proyectos", json=proyecto_valido)

    assert response.status_code == 201
    assert response.json()["proyecto"]["codigo"] == "PRY-PARQUE-01"


def test_evaluacion_economica_parcial(
    client: TestClient, proyecto_valido: dict[str, object]
) -> None:
    client.post("/api/v1/proyectos", json=proyecto_valido)

    response = client.post("/api/v1/proyectos/1/evaluacion-economica")

    assert response.status_code == 200
    body = response.json()
    assert body["proyecto_id"] == 1
    assert body["presupuesto"] == 2_500_000.0
    assert body["beneficiarios"] == 5_000
    assert body["costo_por_habitante"] == 500.0
    assert body["costo_por_beneficiario"] == 500.0
    assert body["score_0_100"] == 0.0
    assert body["costo_excelente"] == 200.0
    assert body["costo_inaceptable"] == 500.0
    assert body["version_criterios"] == 1
    assert body["formula"] == "presupuesto / beneficiarios"
    assert "no mide retorno social" in body["explicacion"]
    assert body["version_algoritmo"] == "economic-cost-per-beneficiary-v1"
    assert body["retorno_socioeconomico"] is None
    assert body["estado_evaluacion"] == "COMPLETADA"
    assert body["advertencias"] == [
        "No se calcula retorno socioeconomico sin datos de beneficios monetizados."
    ]
    guardada = get_evaluacion_economica_repository().obtener_por_proyecto(1)
    assert guardada is not None
    assert float(guardada.costo_por_habitante) == 500.0


def test_evaluacion_economica_bloquea_expediente_incompleto(
    client: TestClient,
) -> None:
    client.post("/api/v1/proyectos", json={"nombre": "Proyecto en borrador"})

    response = client.post("/api/v1/proyectos/1/evaluacion-economica")

    assert response.status_code == 409
    assert response.json()["campos_faltantes"] == [
        "descripcion",
        "ubicacion",
        "presupuesto",
        "beneficiarios",
        "tipo_proyecto",
    ]
    assert get_evaluacion_economica_repository().obtener_por_proyecto(1) is None


def test_evaluacion_economica_proyecto_inexistente_devuelve_404(
    client: TestClient,
) -> None:
    response = client.post("/api/v1/proyectos/999/evaluacion-economica")
    assert response.status_code == 404


def test_evaluacion_juridica_pendiente_de_integracion_rag(
    client: TestClient, proyecto_valido: dict[str, object]
) -> None:
    client.post("/api/v1/proyectos", json=proyecto_valido)

    response = client.post("/api/v1/proyectos/1/evaluacion-juridica")

    assert response.status_code == 200
    assert response.json() == {
        "proyecto_id": 1,
        "estado": "PENDIENTE_VALIDACION_NORMATIVA",
        "cumple": None,
        "observaciones": [
            "Sin fuente normativa verificable no se emite un dictamen; "
            "el caso requiere revision humana y la integracion del servicio RAG."
        ],
        "fuentes": [],
        "requiere_revision": True,
    }
    guardada = get_evaluacion_juridica_repository().obtener_por_proyecto(1)
    assert guardada is not None
    assert guardada.cumple is None


def test_evaluacion_juridica_bloquea_expediente_incompleto(
    client: TestClient,
) -> None:
    client.post("/api/v1/proyectos", json={"nombre": "Proyecto juridico"})

    response = client.post("/api/v1/proyectos/1/evaluacion-juridica")

    assert response.status_code == 409
    assert get_evaluacion_juridica_repository().obtener_por_proyecto(1) is None


def test_evaluacion_juridica_proyecto_inexistente_devuelve_404(
    client: TestClient,
) -> None:
    response = client.post("/api/v1/proyectos/999/evaluacion-juridica")
    assert response.status_code == 404


def test_proyecto_inexistente_devuelve_404(client: TestClient) -> None:
    response = client.get("/api/v1/proyectos/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "No se encontro el proyecto con id 999"}
