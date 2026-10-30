from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from backend.application.dto.pmv1_dto import PMV1ProjectCreate
from backend.application.services.pmv1_services import (
    EconomicProcessor,
    NormativeSearchEngine,
    PlatformService,
)
from backend.domain.exceptions.pmv1_exceptions import ConfiguracionPMV1Error
from backend.infrastructure.config.dependencies import (
    get_auth_service,
    get_platform_service,
)
from backend.main import create_app

PROJECT_ID = UUID("a0000000-0000-4000-a000-00000000000a")
VERSION_ID = UUID("b0000000-0000-4000-a000-00000000000a")
EVALUATION_ID = UUID("d0000000-0000-4000-a000-00000000000a")
EVENT_ID = UUID("e0000000-0000-4000-a000-00000000000a")
ZONING_REVIEW_ID = UUID("11000000-0000-4000-a000-00000000000a")
APPROVAL_ID = UUID("c1000000-0000-4000-a000-000000000001")


class FakeAuth:
    def login(self, email: str, password: str) -> dict[str, Any]:
        if "legal" in email:
            return {
                "access_token": "token-legal",
                "expires_in": 3600,
                "user_id": UUID("10000000-0000-4000-a000-000000000003"),
                "full_name": "Asesor Juridico de prueba",
                "roles": ["LEGAL_ADVISOR"],
            }
        if "admin" in email:
            return {
                "access_token": "token-admin",
                "expires_in": 3600,
                "user_id": UUID("10000000-0000-4000-a000-000000000001"),
                "full_name": "Administrador de prueba",
                "roles": ["ADMIN"],
            }
        return {
            "access_token": "token-prueba",
            "expires_in": 3600,
            "user_id": UUID("10000000-0000-4000-a000-000000000002"),
            "full_name": "Planificador de prueba",
            "roles": ["PLANNER"],
        }

    def decode(self, token: str) -> dict[str, Any]:
        if token == "token-legal":
            return {
                "sub": "10000000-0000-4000-a000-000000000003",
                "roles": ["LEGAL_ADVISOR"],
            }
        if token == "token-admin":
            return {
                "sub": "10000000-0000-4000-a000-000000000001",
                "roles": ["ADMIN"],
            }
        return {
            "sub": "10000000-0000-4000-a000-000000000002",
            "roles": ["PLANNER"],
        }


class FakePlatform:
    def create_project(self, data: PMV1ProjectCreate, actor_id: UUID) -> dict[str, Any]:
        return self.get_project(PROJECT_ID)

    def get_project(self, project_id: UUID) -> dict[str, Any]:
        return {
            "project_id": project_id,
            "project_version_id": VERSION_ID,
            "code": "PRY-A",
            "version_number": 1,
            "status": "ready",
            "title": "Proyecto A",
            "description": "Prueba PMV1",
            "location": "El Tambo, Huancayo",
            "proposed_land_use": "recreacion",
            "territorial_data_origin": "declared",
            "estimated_budget_pen": Decimal("120000.00"),
            "beneficiaries_count": 600,
        }

    def validate_project(self, project_id: UUID) -> dict[str, Any]:
        return {
            "complete": True,
            "status": "ready",
            "missing_fields": [],
            "message": "Expediente completo",
        }

    def request_evaluation(
        self, project_version_id: UUID, actor_id: UUID, idempotency_key: str
    ) -> dict[str, Any]:
        return {
            "evaluation_id": EVALUATION_ID,
            "event_id": EVENT_ID,
            "status": "queued",
            "duplicated": idempotency_key == "repetida",
            "publication_pending": False,
        }

    def get_evaluation(self, evaluation_id: UUID) -> dict[str, Any]:
        return {
            "evaluation_id": evaluation_id,
            "project_version_id": VERSION_ID,
            "criteria_version_id": UUID("c0000000-0000-4000-a000-000000000001"),
            "status": "completed",
            "result": {
                "economic_assessment_id": UUID("f0000000-0000-4000-a000-00000000000a"),
                "cost_per_beneficiary_pen": Decimal("200.00"),
                "score_0_100": Decimal("100.00"),
                "explanation": "presupuesto / beneficiarios",
                "algorithm_version": "economic-cost-per-beneficiary-v1",
            },
        }

    def record_legal_abstention(self, project_id: UUID, actor_id: UUID) -> None:
        return None

    def request_zoning_precheck(
        self, project_id: UUID, actor_id: UUID, idempotency_key: str
    ) -> dict[str, Any]:
        if idempotency_key == "used-by-other-project":
            raise ConfiguracionPMV1Error(
                "Idempotency-Key ya fue utilizada para otro expediente"
            )
        return {
            "review_id": ZONING_REVIEW_ID,
            "project_id": project_id,
            "project_version_id": VERSION_ID,
            "status": "requires_review",
            "compatible": None,
            "location": "El Tambo, Huancayo",
            "proposed_land_use": "recreacion",
            "territorial_data_origin": "declared",
            "evidence": [],
            "alerts": [
                "No se puede concluir compatibilidad sin evidencia territorial versionada."
            ],
            "limitations": "Sin corpus PDU/PDM oficial ni capa GIS.",
            "requires_human_review": True,
            "duplicated": idempotency_key == "zoning-repeat",
        }

    def search_normatives(
        self,
        query: str,
        actor_id: UUID,
        document_filter: str | None = None,
        only_in_force: bool = True,
        limit: int = 5,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if idempotency_key == "normative-conflict":
            raise ConfiguracionPMV1Error("Idempotency-Key ya fue utilizada para otra consulta")

        has_alert_match = "incompatible" in query.lower() or "riesgo" in query.lower()
        if any(term in query.lower() for term in ["inexistente", "marte", "sin_sustento"]):
            results = []
        else:
            results = [
                {
                    "id": "PDUPDM-02" if has_alert_match else "LEY27972-01",
                "document_name": "PDU/PDM Huancayo-El Tambo" if has_alert_match else "Ley N.° 27972",
                "short_code": "PDU_EL_TAMBO" if has_alert_match else "LEY_27972",
                "version": "2026-v1",
                "location": "Art. 89 / Título III" if has_alert_match else "Art. 73",
                "topic": "Compatibilidad de uso de suelo" if has_alert_match else "Competencias municipales",
                "content": (
                    "Resumen didactico simulado: si el uso propuesto para un proyecto es incompatible "
                    "con la zonificacion vigente, el expediente requiere observacion y revision juridica."
                ) if has_alert_match else (
                    "Resumen didactico simulado: las municipalidades ejercen competencias y funciones en asuntos "
                    "de interes local dentro del marco legal correspondiente."
                ),
                "in_force": True,
                "has_alert": has_alert_match,
                "data_origin": "simulated",
                "relevance_score": 85.0 if has_alert_match else 70.0,
            }
        ]
        alerts = [
            f"Alerta legal detectada en {results[0]['id']} ({results[0]['topic']}): {results[0]['content']}"
        ] if (has_alert_match and len(results) > 0) else []

        return {
            "query": query,
            "document_filter": document_filter,
            "total_results": len(results),
            "results": results,
            "alerts_found": alerts,
            "disclaimer": "Material didactico y simulado para el PMV1 en El Tambo.",
            "requires_human_review": bool(alerts),
            "duplicated": idempotency_key == "normative-repeat",
        }

    def list_normative_documents(self) -> list[dict[str, Any]]:
        return [
            {
                "short_code": "DL_1252",
                "document_name": "D. L. N.° 1252 - Invierte.pe",
                "version": "2018-TUO",
                "in_force": True,
                "data_origin": "public",
                "chunks_count": 6,
            },
            {
                "short_code": "LEY_27972",
                "document_name": "Ley N.° 27972 - Ley Orgánica de Municipalidades",
                "version": "2003-v1",
                "in_force": True,
                "data_origin": "public",
                "chunks_count": 6,
            },
            {
                "short_code": "LEY_32069",
                "document_name": "Ley N.° 32069 - Ley General de Contrataciones Públicas",
                "version": "2024-v1",
                "in_force": True,
                "data_origin": "public",
                "chunks_count": 6,
            },
            {
                "short_code": "PDU_EL_TAMBO",
                "document_name": "PDM Huancayo 2017-2037 (O.M. N.° 636-2020-MPH/CM)",
                "version": "2020-OM636",
                "in_force": True,
                "data_origin": "public",
                "chunks_count": 6,
            },
        ]

    def submit_human_approval(
        self,
        project_id: UUID,
        actor_id: UUID,
        decision: str,
        justification: str,
        conditions: str | None,
        idempotency_key: str,
    ) -> dict[str, Any]:
        if idempotency_key == "used-by-other-project":
            raise ConfiguracionPMV1Error("Idempotency-Key ya fue utilizada para otro expediente")
        if decision == "observed" and not conditions:
            raise ConfiguracionPMV1Error("El dictamen 'observed' requiere especificar condiciones u observaciones")
        return {
            "approval_id": APPROVAL_ID,
            "project_id": project_id,
            "project_version_id": VERSION_ID,
            "decision": decision,
            "justification": justification,
            "conditions": conditions,
            "decided_by_user_id": actor_id,
            "idempotency_key": idempotency_key,
            "decided_at": datetime.now(timezone.utc),
            "duplicated": idempotency_key == "approval-repeat",
        }

    def get_human_approval(self, project_id: UUID) -> dict[str, Any]:
        return {
            "project_id": project_id,
            "project_version_id": VERSION_ID,
            "project_status": "evaluated",
            "is_evaluated": True,
            "requires_human_approval": True,
            "current_approval": None,
        }

    def evaluate_social_accessibility(
        self, project_id: UUID, actor_id: UUID, idempotency_key: str | None = None
    ) -> dict[str, Any]:
        if idempotency_key == "social-conflict":
            raise ConfiguracionPMV1Error("Idempotency-Key ya fue utilizada para otro expediente")

        is_pry_b = str(project_id).endswith("b")
        if is_pry_b:
            cats = [
                {
                    "category": "salud",
                    "category_label": "Accesibilidad a Salud",
                    "status": "sufficient",
                    "has_sufficient_data": True,
                    "indicator": "Distancia peatonal al establecimiento de salud de primer nivel",
                    "value": 680.0,
                    "unit": "metros",
                    "source": "RENAES MINSA (Simulado)",
                    "data_origin": "simulated",
                    "is_simulated": True,
                    "message": "Centro de Salud El Tambo a 680 metros.",
                },
                {
                    "category": "educacion",
                    "category_label": "Accesibilidad a Educación",
                    "status": "insufficient",
                    "has_sufficient_data": False,
                    "indicator": "Distancia a la institución educativa pública inicial/primaria más cercana",
                    "value": None,
                    "unit": None,
                    "source": "Catastro Municipal (Sin cobertura de padrón escolar)",
                    "data_origin": "simulated",
                    "is_simulated": True,
                    "message": "Información insuficiente",
                },
                {
                    "category": "transporte",
                    "category_label": "Accesibilidad a Transporte",
                    "status": "insufficient",
                    "has_sufficient_data": False,
                    "indicator": "Tiempo de caminata al paradero o eje de transporte público más cercano",
                    "value": None,
                    "unit": None,
                    "source": "Catastro Municipal (Sin cobertura de rutas autorizadas)",
                    "data_origin": "simulated",
                    "is_simulated": True,
                    "message": "Información insuficiente",
                },
            ]
            summary = "Análisis de accesibilidad social parcial: 1 categoría(s) con datos suficientes y 2 con Información insuficiente."
            status = "partial"
        else:
            cats = [
                {
                    "category": "salud",
                    "category_label": "Accesibilidad a Salud",
                    "status": "sufficient",
                    "has_sufficient_data": True,
                    "indicator": "Distancia peatonal al establecimiento de salud de primer nivel",
                    "value": 450.0,
                    "unit": "metros",
                    "source": "RENAES MINSA (Simulado)",
                    "data_origin": "simulated",
                    "is_simulated": True,
                    "message": "Puesto de Salud El Tambo I a 450 metros.",
                },
                {
                    "category": "educacion",
                    "category_label": "Accesibilidad a Educación",
                    "status": "sufficient",
                    "has_sufficient_data": True,
                    "indicator": "Distancia a la institución educativa pública inicial/primaria más cercana",
                    "value": 320.0,
                    "unit": "metros",
                    "source": "Censo Educativo MINEDU (Simulado)",
                    "data_origin": "simulated",
                    "is_simulated": True,
                    "message": "I.E. Primaria N.° 30154 a 320 metros.",
                },
                {
                    "category": "transporte",
                    "category_label": "Accesibilidad a Transporte",
                    "status": "sufficient",
                    "has_sufficient_data": True,
                    "indicator": "Tiempo de caminata al paradero o eje de transporte público más cercano",
                    "value": 6.0,
                    "unit": "minutos",
                    "source": "Sistema Vial Metropolitano (Simulado)",
                    "data_origin": "simulated",
                    "is_simulated": True,
                    "message": "Paradero Av. Mariscal Castilla a 6 minutos a pie.",
                },
            ]
            summary = "Análisis de accesibilidad social completo. Se identificaron indicadores territoriales para salud, educación y transporte."
            status = "complete"

        return {
            "project_id": project_id,
            "project_code": "PRY-B" if is_pry_b else "PRY-A",
            "project_version_id": VERSION_ID,
            "status": status,
            "summary": summary,
            "categories": cats,
            "evaluated_at": datetime.now(timezone.utc),
            "duplicated": idempotency_key == "social-repeat",
        }

    def get_social_accessibility(self, project_id: UUID) -> dict[str, Any]:
        return self.evaluate_social_accessibility(project_id, UUID("10000000-0000-4000-a000-000000000002"))

    def evaluate_environmental_assessment(
        self, project_id: UUID, actor_id: UUID, idempotency_key: str | None = None
    ) -> dict[str, Any]:
        if idempotency_key == "env-conflict":
            raise ConfiguracionPMV1Error("Idempotency-Key ya fue utilizada para otro expediente")

        is_pry_b = str(project_id).endswith("b")
        is_pry_c = str(project_id).endswith("c")

        if is_pry_b:
            return {
                "project_id": project_id,
                "project_code": "PRY-B",
                "project_version_id": VERSION_ID,
                "status": "insufficient",
                "risk_level": "insufficient",
                "risk_level_label": "Información insuficiente",
                "risk_observation": None,
                "requires_human_review": False,
                "favorable": None,
                "favorable_label": "Sin conclusión favorable: información insuficiente",
                "summary": "Información insuficiente: el expediente no cuenta con datos ambientales esenciales, Declaración de Impacto Ambiental (DIA) ni línea base territorial verificable.",
                "declared_vs_evidence": {
                    "declared_by_applicant": None,
                    "declared_measures": None,
                    "verifiable_evidence": None,
                    "evidence_source": "Catastro Municipal El Tambo (Sin cobertura)",
                    "is_simulated": True,
                    "proximity_to_water_meters": None,
                    "is_in_protected_or_risk_area": None,
                },
                "impacts": [],
                "mitigations": [],
                "evaluated_at": datetime.now(timezone.utc),
                "duplicated": idempotency_key == "env-repeat",
            }

        if is_pry_c:
            return {
                "project_id": project_id,
                "project_code": "PRY-C",
                "project_version_id": VERSION_ID,
                "status": "sufficient",
                "risk_level": "high",
                "risk_level_label": "Riesgo Alto",
                "risk_observation": "OBSERVACIÓN DE RIESGO AMBIENTAL ALTO: Ubicación a 25 metros del Río Shullcas en faja marginal intangible no mitigable. Se prohíbe la aprobación automática. Requiere consideración técnica ambiental humana obligatoria antes de cualquier decisión favorable.",
                "requires_human_review": True,
                "favorable": None,
                "favorable_label": "No favorable - Requiere revisión técnica ambiental humana obligatoria",
                "summary": "Alerta ambiental: se identificó un nivel de riesgo ambiental ALTO. El expediente requiere pronunciamiento técnico humano formal antes de una decisión favorable.",
                "declared_vs_evidence": {
                    "declared_by_applicant": "Almacenamiento de vehículos sin impacto ambiental.",
                    "declared_measures": "Piso de afirmado compacto.",
                    "verifiable_evidence": "Predio ubicado a 25 metros del Río Shullcas en faja marginal intangible no mitigable (PDM Huancayo / CENEPRED-SIGRID).",
                    "evidence_source": "Dataset ambiental simulado SIPRIM El Tambo - PDM Huancayo / SIGRID (Simulado)",
                    "is_simulated": True,
                    "proximity_to_water_meters": 25.0,
                    "is_in_protected_or_risk_area": True,
                },
                "impacts": [
                    {
                        "component": "recurso_hidrico",
                        "component_label": "Recurso Hídrico y Faja Marginal",
                        "description": "Riesgo severo de contaminación por vertimientos de hidrocarburos y alteración fluvial.",
                        "severity": "alta",
                        "substantiation": "Ubicación en faja marginal no mitigable (<30 m de cauce).",
                        "mitigations": [
                            "Reubicación fuera de la faja marginal intangible",
                            "Instalación de trampas de grasa certificadas",
                        ],
                    }
                ],
                "mitigations": [
                    {
                        "component": "recurso_hidrico",
                        "measure": "Delimitación estricta y retiro obligatorio del cauce fluvial según plano PDM Huancayo.",
                        "type": "preventiva",
                        "origin": "requerimiento_tecnico",
                    }
                ],
                "evaluated_at": datetime.now(timezone.utc),
                "duplicated": idempotency_key == "env-repeat",
            }

        return {
            "project_id": project_id,
            "project_code": "PRY-A",
            "project_version_id": VERSION_ID,
            "status": "sufficient",
            "risk_level": "moderate",
            "risk_level_label": "Riesgo Moderado",
            "risk_observation": None,
            "requires_human_review": False,
            "favorable": True,
            "favorable_label": "Favorable condicionado a cumplimiento de mitigaciones",
            "summary": "Evaluación ambiental con riesgo MODERADO: impactos de obra mitigables mediante las medidas ambientales programadas.",
            "declared_vs_evidence": {
                "declared_by_applicant": "Polvo y ruido temporal durante obras civiles.",
                "declared_measures": "Aspersión diaria y cerco perimétrico con malla antipolvo.",
                "verifiable_evidence": "Ubicación en zona urbana consolidada, fuera de áreas naturales o de riesgo fluvial.",
                "evidence_source": "Dataset ambiental simulado SIPRIM El Tambo - PDM Huancayo (Simulado)",
                "is_simulated": True,
                "proximity_to_water_meters": 420.0,
                "is_in_protected_or_risk_area": False,
            },
            "impacts": [
                {
                    "component": "aire_acustico",
                    "component_label": "Emisiones Atmosféricas y Ruido",
                    "description": "Generación temporal de polvo y niveles sonoros moderados.",
                    "severity": "moderada",
                    "substantiation": "Obras en trama urbana consolidada.",
                    "mitigations": [
                        "Aspersión de agua diaria",
                        "Horario de trabajo diurno restringido",
                    ],
                }
            ],
            "mitigations": [
                {
                    "component": "aire_acustico",
                    "measure": "Riego periódico de calzadas y cerco con lona antipolvo.",
                    "type": "preventiva",
                    "origin": "propuesta_expediente",
                }
            ],
            "evaluated_at": datetime.now(timezone.utc),
            "duplicated": idempotency_key == "env-repeat",
        }

    def get_environmental_assessment(self, project_id: UUID) -> dict[str, Any]:
        return self.evaluate_environmental_assessment(project_id, UUID("10000000-0000-4000-a000-000000000002"))



@pytest.fixture
def client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: FakeAuth()
    app.dependency_overrides[get_platform_service] = lambda: FakePlatform()
    with TestClient(app) as test_client:
        yield test_client


def test_ruta_oficial_exige_autenticacion(client: TestClient) -> None:
    response = client.get(f"/api/v1/projects/{PROJECT_ID}")
    assert response.status_code == 401


def test_hu11_carga_una_vez_y_encola_evaluacion(client: TestClient) -> None:
    headers = {"Authorization": "Bearer token-prueba"}
    created = client.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "code": "PRY-A",
            "title": "Proyecto A",
            "description": "Prueba PMV1",
            "location": "El Tambo, Huancayo",
            "proposed_land_use": "recreacion",
            "estimated_budget_pen": 120000,
            "beneficiaries_count": 600,
        },
    )
    assert created.status_code == 201
    assert created.json()["project_version_id"] == str(VERSION_ID)

    queued = client.post(
        "/api/v1/evaluations",
        headers={**headers, "Idempotency-Key": "solicitud-1"},
        json={"project_version_id": str(VERSION_ID)},
    )
    assert queued.status_code == 202
    assert queued.json()["status"] == "queued"
    assert queued.json()["duplicated"] is False


def test_hu12_reporta_campos_faltantes_antes_de_persistir() -> None:
    data = PMV1ProjectCreate(title="Proyecto incompleto")
    missing = PlatformService._missing(data)
    assert missing == [
        "description",
        "location",
        "proposed_land_use",
        "estimated_budget_pen",
        "beneficiaries_count",
    ]


def test_hu13_formula_documentada_y_sin_retorno_inventado(client: TestClient) -> None:
    cost_a, score_a = EconomicProcessor.calculate(
        Decimal(120000), 600, Decimal(200), Decimal(500)
    )
    cost_b, score_b = EconomicProcessor.calculate(
        Decimal(90000), 300, Decimal(200), Decimal(500)
    )
    assert (cost_a, score_a) == (Decimal("200.00"), Decimal("100.00"))
    assert (cost_b, score_b) == (Decimal("300.00"), Decimal("66.67"))

    response = client.get(
        f"/api/v1/evaluations/{EVALUATION_ID}",
        headers={"Authorization": "Bearer token-prueba"},
    )
    assert response.status_code == 200
    assert response.json()["result"]["socioeconomic_return"] is None


def test_hu110_se_abstiene_sin_fuentes_normativas(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/legal-precheck",
        headers={"Authorization": "Bearer token-prueba"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["complies"] is None
    assert body["sources"] == []
    assert body["requires_review"] is True


def test_hu111_zonificacion_se_abstiene_y_exige_evidencia(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/zoning-precheck",
        headers={
            "Authorization": "Bearer token-prueba",
            "Idempotency-Key": "zoning-1",
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "requires_review"
    assert body["compatible"] is None
    assert body["evidence"] == []
    assert body["requires_human_review"] is True
    assert "evidencia territorial versionada" in body["alerts"][0]


def test_hu111_requiere_clave_de_idempotencia(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/zoning-precheck",
        headers={"Authorization": "Bearer token-prueba"},
    )
    assert response.status_code == 422


def test_hu111_no_reutiliza_clave_de_otro_expediente(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/zoning-precheck",
        headers={
            "Authorization": "Bearer token-prueba",
            "Idempotency-Key": "used-by-other-project",
        },
    )
    assert response.status_code == 409
    assert "otro expediente" in response.json()["detail"]


def test_hu21_busqueda_normativa_requiere_autenticacion(client: TestClient) -> None:
    response = client.post("/api/v1/normative/search", json={"query": "competencias"})
    assert response.status_code == 401


def test_hu21_busqueda_normativa_prohibida_para_planner(client: TestClient) -> None:
    response = client.post(
        "/api/v1/normative/search",
        headers={"Authorization": "Bearer token-prueba"},
        json={"query": "competencias municipales"},
    )
    assert response.status_code == 403
    assert "LEGAL_ADVISOR o ADMIN" in response.json()["detail"]


def test_hu21_busqueda_normativa_permitida_para_legal_advisor(client: TestClient) -> None:
    response = client.post(
        "/api/v1/normative/search",
        headers={"Authorization": "Bearer token-legal"},
        json={"query": "competencias municipales"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_results"] >= 1
    assert body["results"][0]["id"] == "LEY27972-01"
    assert body["results"][0]["relevance_score"] > 0
    assert body["requires_human_review"] is False
    assert "Material didactico" in body["disclaimer"]


def test_hu21_busqueda_normativa_permitida_para_admin(client: TestClient) -> None:
    response = client.post(
        "/api/v1/normative/search",
        headers={"Authorization": "Bearer token-admin"},
        json={"query": "competencias municipales"},
    )
    assert response.status_code == 200


def test_hu21_busqueda_normativa_detecta_alerta_y_exige_revision_humana(client: TestClient) -> None:
    response = client.post(
        "/api/v1/normative/search",
        headers={"Authorization": "Bearer token-legal"},
        json={"query": "uso de suelo incompatible con zonificacion"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["has_alert"] is True
    assert body["results"][0]["id"] == "PDUPDM-02"
    assert body["requires_human_review"] is True
    assert len(body["alerts_found"]) >= 1
    assert "Alerta legal detectada" in body["alerts_found"][0]


def test_hu21_busqueda_normativa_idempotente(client: TestClient) -> None:
    response = client.post(
        "/api/v1/normative/search",
        headers={
            "Authorization": "Bearer token-legal",
            "Idempotency-Key": "normative-repeat",
        },
        json={"query": "competencias municipales"},
    )
    assert response.status_code == 200
    assert response.json()["duplicated"] is True


def test_hu21_busqueda_normativa_conflicto_idempotencia(client: TestClient) -> None:
    response = client.post(
        "/api/v1/normative/search",
        headers={
            "Authorization": "Bearer token-legal",
            "Idempotency-Key": "normative-conflict",
        },
        json={"query": "consulta diferente"},
    )
    assert response.status_code == 409
    assert "otra consulta" in response.json()["detail"]


def test_hu21_listar_documentos_normativos(client: TestClient) -> None:
    # Prohibido para PLANNER
    res_planner = client.get(
        "/api/v1/normative/documents",
        headers={"Authorization": "Bearer token-prueba"},
    )
    assert res_planner.status_code == 403

    # Permitido para LEGAL_ADVISOR
    res_legal = client.get(
        "/api/v1/normative/documents",
        headers={"Authorization": "Bearer token-legal"},
    )
    assert res_legal.status_code == 200
    body = res_legal.json()
    assert body["total_documents"] == 4
    codes = [d["short_code"] for d in body["documents"]]
    assert "LEY_27972" in codes
    assert "PDU_EL_TAMBO" in codes
    assert "DL_1252" in codes
    assert "LEY_32069" in codes


def test_hu21_busqueda_normativa_incluye_ubicacion_identificable(client: TestClient) -> None:
    response = client.post(
        "/api/v1/normative/search",
        headers={"Authorization": "Bearer token-legal"},
        json={"query": "competencias municipales"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_results"] >= 1
    hit = body["results"][0]
    assert "Ley" in hit["document_name"]
    assert hit["version"] == "2026-v1"
    assert hit["location"] == "Art. 73"
    assert hit["id"] == "LEY27972-01"


def test_hu21_busqueda_normativa_sin_evidencia_devuelve_cero_resultados(client: TestClient) -> None:
    response = client.post(
        "/api/v1/normative/search",
        headers={"Authorization": "Bearer token-legal"},
        json={"query": "sin_sustento tema espacial inexistente"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_results"] == 0
    assert len(body["results"]) == 0


def test_hu21_motor_ponderacion_scoring() -> None:

    chunk = {
        "id": "PDUPDM-02",
        "document_name": "PDU/PDM Huancayo-El Tambo",
        "short_code": "PDU_EL_TAMBO",
        "topic": "Compatibilidad de uso de suelo",
        "content": "Resumen didáctico simulado: si el uso propuesto para un proyecto es incompatible con la zonificación vigente, el expediente requiere observación y revisión jurídica.",
        "has_alert": True,
    }

    kw = NormativeSearchEngine.extract_keywords("uso de suelo incompatible")
    assert "uso" in kw
    assert "suelo" in kw
    assert "incompatible" in kw
    assert "de" not in kw  # Stop word eliminada

    score = NormativeSearchEngine.score_chunk(chunk, "uso de suelo incompatible", kw)
    assert score > 50.0  # Coincide en topic, content y alerta


def test_human_approval_exige_autenticacion(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/approval",
        json={"decision": "approved", "justification": "Aprobado"},
    )
    assert response.status_code == 401


def test_human_approval_prohibido_para_planner_y_legal(client: TestClient) -> None:
    # Planner no tiene permiso de aprobacion formal
    res_planner = client.post(
        f"/api/v1/projects/{PROJECT_ID}/approval",
        headers={
            "Authorization": "Bearer token-prueba",
            "Idempotency-Key": "appr-planner",
        },
        json={"decision": "approved", "justification": "Intento planificador"},
    )
    assert res_planner.status_code == 403
    assert "ADMIN" in res_planner.json()["detail"]

    # Legal advisor tampoco emite la aprobacion ejecutiva
    res_legal = client.post(
        f"/api/v1/projects/{PROJECT_ID}/approval",
        headers={
            "Authorization": "Bearer token-legal",
            "Idempotency-Key": "appr-legal",
        },
        json={"decision": "approved", "justification": "Intento asesor legal"},
    )
    assert res_legal.status_code == 403
    assert "ADMIN" in res_legal.json()["detail"]


def test_human_approval_requiere_idempotency_key(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/approval",
        headers={"Authorization": "Bearer token-admin"},
        json={"decision": "approved", "justification": "Aprobado por el Administrador"},
    )
    assert response.status_code == 422


def test_human_approval_requiere_condiciones_cuando_observed(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/approval",
        headers={
            "Authorization": "Bearer token-admin",
            "Idempotency-Key": "appr-obs-missing",
        },
        json={"decision": "observed", "justification": "Se observan faltantes tecnicos"},
    )
    assert response.status_code == 422


def test_human_approval_exitoso_para_admin(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/approval",
        headers={
            "Authorization": "Bearer token-admin",
            "Idempotency-Key": "appr-admin-ok",
        },
        json={
            "decision": "approved",
            "justification": "Proyecto social y tecnicamente viable segun evaluacion economica.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "approved"
    assert body["approval_id"] == str(APPROVAL_ID)
    assert body["project_id"] == str(PROJECT_ID)
    assert body["project_version_id"] == str(VERSION_ID)
    assert body["duplicated"] is False


def test_human_approval_observado_con_condiciones(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/approval",
        headers={
            "Authorization": "Bearer token-admin",
            "Idempotency-Key": "appr-admin-obs",
        },
        json={
            "decision": "observed",
            "justification": "Requiere mayor detalle en el cronograma.",
            "conditions": "Presentar informe geotécnico complementario antes de licitación.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "observed"
    assert body["conditions"] == "Presentar informe geotécnico complementario antes de licitación."


def test_human_approval_idempotencia(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/approval",
        headers={
            "Authorization": "Bearer token-admin",
            "Idempotency-Key": "approval-repeat",
        },
        json={
            "decision": "approved",
            "justification": "Dictamen repetido",
        },
    )
    assert response.status_code == 200
    assert response.json()["duplicated"] is True


def test_human_approval_conflicto_idempotencia(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/approval",
        headers={
            "Authorization": "Bearer token-admin",
            "Idempotency-Key": "used-by-other-project",
        },
        json={
            "decision": "approved",
            "justification": "Dictamen en conflicto",
        },
    )
    assert response.status_code == 409
    assert "otro expediente" in response.json()["detail"]


def test_get_human_approval_status(client: TestClient) -> None:
    response = client.get(
        f"/api/v1/projects/{PROJECT_ID}/approval",
        headers={"Authorization": "Bearer token-prueba"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == str(PROJECT_ID)
    assert body["project_status"] == "evaluated"
    assert body["is_evaluated"] is True
    assert body["requires_human_approval"] is True

def test_api_servicio_no_disponible_retorna_503_controlado(client: TestClient) -> None:
    class FailingPlatform(FakePlatform):
        def search_normatives(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
            from backend.domain.exceptions.pmv1_exceptions import ServicioNoDisponibleError
            raise ServicioNoDisponibleError("Servicio de normativa no disponible: la base de datos no responde.")

    app = client.app
    app.dependency_overrides[get_platform_service] = lambda: FailingPlatform()
    try:
        response = client.post(
            "/api/v1/normative/search",
            headers={"Authorization": "Bearer token-legal"},
            json={"query": "obras municipales"},
        )
        assert response.status_code == 503
        assert "no disponible" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides[get_platform_service] = lambda: FakePlatform()

def test_social_assessment_requires_auth(client: TestClient) -> None:
    response = client.post(f"/api/v1/projects/{PROJECT_ID}/social-assessment")
    assert response.status_code == 401


def test_social_assessment_requires_planner_role(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/social-assessment",
        headers={"Authorization": "Bearer token-legal"},
    )
    assert response.status_code == 403


def test_social_assessment_pry_a_complete(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/social-assessment",
        headers={"Authorization": "Bearer token-prueba"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "complete"
    assert len(body["categories"]) == 3
    cats = {c["category"]: c for c in body["categories"]}
    assert cats["salud"]["has_sufficient_data"] is True
    assert cats["salud"]["value"] == 450.0
    assert cats["educacion"]["has_sufficient_data"] is True
    assert cats["educacion"]["value"] == 320.0
    assert cats["transporte"]["has_sufficient_data"] is True
    assert cats["transporte"]["value"] == 6.0


def test_social_assessment_pry_b_insufficient_no_numbers(client: TestClient) -> None:
    project_b_id = UUID("a0000000-0000-4000-a000-00000000000b")
    response = client.post(
        f"/api/v1/projects/{project_b_id}/social-assessment",
        headers={"Authorization": "Bearer token-prueba"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partial"
    cats = {c["category"]: c for c in body["categories"]}

    # Salud con datos
    assert cats["salud"]["has_sufficient_data"] is True
    assert cats["salud"]["value"] == 680.0

    # Educación: Información insuficiente y estrictamente NINGÚN número inventado
    assert cats["educacion"]["has_sufficient_data"] is False
    assert cats["educacion"]["message"] == "Información insuficiente"
    assert cats["educacion"]["value"] is None
    assert cats["educacion"]["unit"] is None

    # Transporte: Información insuficiente y estrictamente NINGÚN número inventado
    assert cats["transporte"]["has_sufficient_data"] is False
    assert cats["transporte"]["message"] == "Información insuficiente"
    assert cats["transporte"]["value"] is None
    assert cats["transporte"]["unit"] is None


def test_get_social_assessment(client: TestClient) -> None:
    response = client.get(
        f"/api/v1/projects/{PROJECT_ID}/social-assessment",
        headers={"Authorization": "Bearer token-prueba"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "complete"
    assert len(body["categories"]) == 3

def test_environmental_assessment_requires_auth(client: TestClient) -> None:
    response = client.post(f"/api/v1/projects/{PROJECT_ID}/environmental-assessment")
    assert response.status_code == 401


def test_environmental_assessment_requires_planner_role(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/environmental-assessment",
        headers={"Authorization": "Bearer token-legal"},
    )
    assert response.status_code == 403


def test_environmental_assessment_pry_a_complete(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/environmental-assessment",
        headers={"Authorization": "Bearer token-prueba"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "sufficient"
    assert body["risk_level"] == "moderate"
    assert body["favorable"] is True
    assert body["requires_human_review"] is False
    assert len(body["impacts"]) >= 1
    assert len(body["mitigations"]) >= 1
    d_vs_e = body["declared_vs_evidence"]
    assert d_vs_e["declared_by_applicant"] is not None
    assert d_vs_e["verifiable_evidence"] is not None
    assert d_vs_e["is_simulated"] is True


def test_environmental_assessment_pry_c_high_risk_requires_human_review(client: TestClient) -> None:
    project_c_id = UUID("a0000000-0000-4000-a000-00000000000c")
    response = client.post(
        f"/api/v1/projects/{project_c_id}/environmental-assessment",
        headers={"Authorization": "Bearer token-prueba"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "sufficient"
    assert body["risk_level"] == "high"
    assert body["requires_human_review"] is True
    # NO aprobación automática
    assert body["favorable"] is not True
    assert body["risk_observation"] is not None
    assert "OBSERVACIÓN DE RIESGO AMBIENTAL ALTO" in body["risk_observation"]


def test_environmental_assessment_pry_b_insufficient_no_favorable(client: TestClient) -> None:
    project_b_id = UUID("a0000000-0000-4000-a000-00000000000b")
    response = client.post(
        f"/api/v1/projects/{project_b_id}/environmental-assessment",
        headers={"Authorization": "Bearer token-prueba"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "insufficient"
    assert body["risk_level"] == "insufficient"
    assert body["risk_level_label"] == "Información insuficiente"
    # NUNCA favorable por defecto
    assert body["favorable"] is None
    assert body["favorable"] is not True
    assert "Información insuficiente" in body["summary"]
    assert body["declared_vs_evidence"]["is_in_protected_or_risk_area"] is None
    assert body["declared_vs_evidence"]["is_in_protected_or_risk_area"] is not False


def test_get_environmental_assessment(client: TestClient) -> None:
    response = client.get(
        f"/api/v1/projects/{PROJECT_ID}/environmental-assessment",
        headers={"Authorization": "Bearer token-prueba"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "sufficient"
    assert body["risk_level"] == "moderate"

