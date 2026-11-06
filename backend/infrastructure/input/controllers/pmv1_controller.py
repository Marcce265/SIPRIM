from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, status

from backend.application.dto.evaluacion_ia_dto import DictamenIAResponse
from backend.application.dto.pmv1_dto import (
    CheckpointResponse,
    CheckpointResumeRequest,
    CheckpointResumeResponse,
    EvaluationAccepted,
    EvaluationCreate,
    EvaluationResponse,
    HumanApprovalCreate,
    HumanApprovalResponse,
    HumanApprovalStatusResponse,
    LegalAlertResolveRequest,
    LegalAlertResolutionResponse,
    LegalAssessmentResponse,
    LegalPrecheckResponse,
    LoginRequest,
    LoginResponse,
    NormativeDocumentListResponse,
    NormativeSearchRequest,
    NormativeSearchResponse,
    PertEstimateCreate,
    PertEstimateResponse,
    PMV1ProjectCreate,
    PMV1ProjectResponse,
    PMV1ValidationResponse,
    EnvironmentalAssessmentResponse,
    SocialAccessibilityResponse,
    TechnicalFeasibilityResponse,
    UnifiedAssessmentSummaryResponse,
    ZoningPrecheckResponse,
)
from backend.application.services.pmv1_services import AuthService, PlatformService
from backend.domain.exceptions.ia_exceptions import (
    IAAuthenticationError,
    IAConfigurationError,
    IAError,
    IAGraphError,
    IARateLimitError,
    IATimeoutError,
)
from backend.domain.exceptions.pmv1_exceptions import ExpedientePMV1IncompletoError
from backend.domain.ports.ia_service_port import IAServicePort
from backend.infrastructure.config.dependencies import (
    get_auth_service,
    get_ia_service,
    get_platform_service,
    require_admin,
    require_legal_advisor,
    require_legal_or_planner,
    require_planner,
)

router = APIRouter(prefix="/api/v1", tags=["PMV1 oficial"])


@router.post("/auth/login", response_model=LoginResponse)
def login(
    data: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> dict[str, Any]:
    return service.login(data.email, data.password)


@router.post(
    "/projects", response_model=PMV1ProjectResponse, status_code=status.HTTP_201_CREATED
)
def create_project(
    data: PMV1ProjectCreate,
    user: Annotated[dict[str, Any], Depends(require_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
) -> dict[str, Any]:
    return service.create_project(data, UUID(user["sub"]))


@router.get("/projects/by-code/{code}", response_model=PMV1ProjectResponse)
def get_project_by_code(
    code: Annotated[str, Path(min_length=3, max_length=40)],
    _: Annotated[dict[str, Any], Depends(require_legal_or_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
) -> dict[str, Any]:
    return service.get_project_by_code(code)


@router.get("/projects/{project_id}", response_model=PMV1ProjectResponse)
def get_project(
    project_id: Annotated[UUID, Path()],
    _: Annotated[dict[str, Any], Depends(require_legal_or_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
) -> dict[str, Any]:
    return service.get_project(project_id)


@router.get(
    "/projects/{project_id}/checkpoint",
    response_model=CheckpointResponse | None,
    summary="Consulta el punto de control persistente del proyecto ante riesgo alto (HU3.1 / HU3.4)",
)
def get_project_checkpoint(
    project_id: Annotated[UUID, Path()],
    _: Annotated[dict[str, Any], Depends(require_legal_or_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
) -> dict[str, Any] | None:
    return service.get_project_checkpoint(project_id)


@router.post(
    "/projects/{project_id}/checkpoint/resume",
    response_model=CheckpointResumeResponse,
    status_code=status.HTTP_200_OK,
    summary="Reanuda la evaluación desde un checkpoint HITL persistente autorizado por Gerencia (HU3.4)",
)
def resume_project_checkpoint(
    project_id: Annotated[UUID, Path()],
    payload: CheckpointResumeRequest,
    user: Annotated[dict[str, Any], Depends(require_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=1, max_length=128)
    ],
) -> dict[str, Any]:
    return service.resume_project_checkpoint(
        project_id=project_id,
        actor_id=UUID(user["sub"]),
        justification=payload.justification,
        conditions=payload.conditions,
        idempotency_key=idempotency_key,
    )


@router.post("/projects/{project_id}/validate", response_model=PMV1ValidationResponse)
def validate_project(
    project_id: Annotated[UUID, Path()],
    _: Annotated[dict[str, Any], Depends(require_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
) -> dict[str, Any]:
    return service.validate_project(project_id)


@router.post(
    "/projects/{project_id}/evaluacion-ia",
    response_model=DictamenIAResponse,
    summary="Dictamen preliminar Gemini sobre un expediente PMV1",
)
async def evaluar_proyecto_pmv1_ia(
    project_id: Annotated[UUID, Path()],
    _: Annotated[dict[str, Any], Depends(require_planner)],
    platform: Annotated[PlatformService, Depends(get_platform_service)],
    ia_service: Annotated[IAServicePort, Depends(get_ia_service)],
) -> DictamenIAResponse:
    project = platform.get_project(project_id)
    missing = [
        field
        for field in (
            "title",
            "description",
            "location",
            "proposed_land_use",
            "estimated_budget_pen",
            "beneficiaries_count",
        )
        if project.get(field) in (None, "")
    ]
    if missing:
        raise ExpedientePMV1IncompletoError(missing)
    ficha = {
        "id": str(project_id),
        "codigo": project.get("code"),
        "nombre": project["title"],
        "descripcion": project["description"],
        "ubicacion": project["location"],
        "presupuesto": float(project["estimated_budget_pen"]),
        "beneficiarios": project["beneficiaries_count"],
        "tipo_proyecto": project["proposed_land_use"],
    }
    try:
        dictamen = await ia_service.generar_dictamen(ficha)
    except IAError as exc:
        status_code = 502
        if isinstance(exc, (IAConfigurationError, IAAuthenticationError)):
            status_code = 503
        elif isinstance(exc, IARateLimitError):
            status_code = 429
        elif isinstance(exc, IATimeoutError):
            status_code = 504
        elif isinstance(exc, IAGraphError):
            status_code = 500
        raise HTTPException(
            status_code=status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from None
    return DictamenIAResponse.model_validate(dictamen)


@router.post(
    "/evaluations",
    response_model=EvaluationAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_evaluation(
    data: EvaluationCreate,
    user: Annotated[dict[str, Any], Depends(require_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=1, max_length=120)
    ],
) -> dict[str, Any]:
    return service.request_evaluation(
        data.project_version_id, UUID(user["sub"]), idempotency_key
    )


@router.get("/evaluations/{evaluation_id}", response_model=EvaluationResponse)
def get_evaluation(
    evaluation_id: Annotated[UUID, Path()],
    _: Annotated[dict[str, Any], Depends(require_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
) -> dict[str, Any]:
    return service.get_evaluation(evaluation_id)


@router.post(
    "/projects/{project_id}/legal-precheck", response_model=LegalPrecheckResponse
)
def legal_precheck(
    project_id: Annotated[UUID, Path()],
    user: Annotated[dict[str, Any], Depends(require_legal_or_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
) -> dict[str, Any]:
    res = service.record_legal_abstention(project_id, UUID(user["sub"]))
    if isinstance(res, dict):
        return res
    return {"project_id": project_id}


@router.get(
    "/projects/{project_id}/legal-assessment", response_model=LegalAssessmentResponse
)
def get_legal_assessment(
    project_id: Annotated[UUID, Path()],
    _: Annotated[dict[str, Any], Depends(require_legal_or_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
) -> dict[str, Any]:
    return service.get_legal_assessment(project_id)


@router.post(
    "/projects/{project_id}/legal-assessment", response_model=LegalAssessmentResponse
)
def evaluate_legal_assessment(
    project_id: Annotated[UUID, Path()],
    user: Annotated[dict[str, Any], Depends(require_legal_or_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", max_length=120)
    ] = None,
) -> dict[str, Any]:
    return service.evaluate_legal_assessment(
        project_id, UUID(user["sub"]), idempotency_key=idempotency_key
    )


@router.post(
    "/projects/{project_id}/legal-alert/resolve",
    response_model=LegalAlertResolutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Levanta formalmente una alerta legal por un asesor jurídico autorizado (HU2.3)",
)
def resolve_legal_alert(
    project_id: Annotated[UUID, Path()],
    payload: LegalAlertResolveRequest,
    user: Annotated[dict[str, Any], Depends(require_legal_advisor)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=1, max_length=120)
    ],
) -> dict[str, Any]:
    return service.resolve_legal_alert(
        project_id=project_id,
        actor_id=UUID(user["sub"]),
        resolution_action=payload.resolution_action,
        justification=payload.justification,
        idempotency_key=idempotency_key,
        evidence_reference=payload.evidence_reference,
    )


@router.post(
    "/projects/{project_id}/zoning-precheck",
    response_model=ZoningPrecheckResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def zoning_precheck(
    project_id: Annotated[UUID, Path()],
    user: Annotated[dict[str, Any], Depends(require_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=1, max_length=120)
    ],
) -> dict[str, Any]:
    return service.request_zoning_precheck(
        project_id, UUID(user["sub"]), idempotency_key
    )


@router.post("/normative/search", response_model=NormativeSearchResponse)
def search_normative(
    data: NormativeSearchRequest,
    user: Annotated[dict[str, Any], Depends(require_legal_advisor)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", max_length=120)
    ] = None,
) -> dict[str, Any]:
    return service.search_normatives(
        query=data.query,
        actor_id=UUID(user["sub"]),
        document_filter=data.document_filter,
        only_in_force=data.only_in_force,
        limit=data.limit,
        idempotency_key=idempotency_key,
    )


@router.get("/normative/documents", response_model=NormativeDocumentListResponse)
def list_normative_documents(
    _: Annotated[dict[str, Any], Depends(require_legal_advisor)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
) -> dict[str, Any]:
    docs = service.list_normative_documents()
    return {
        "total_documents": len(docs),
        "documents": docs,
        "disclaimer": (
            "Corpus normativo versionado para el PMV1 en El Tambo. "
            "Las fuentes activas son referenciales y requieren verificacion humana."
        ),
    }


@router.post(
    "/projects/{project_id}/approval",
    response_model=HumanApprovalResponse,
    status_code=status.HTTP_200_OK,
)
def submit_human_approval(
    project_id: Annotated[UUID, Path()],
    data: HumanApprovalCreate,
    user: Annotated[dict[str, Any], Depends(require_admin)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=1, max_length=120)
    ],
) -> dict[str, Any]:
    return service.submit_human_approval(
        project_id=project_id,
        actor_id=UUID(user["sub"]),
        decision=data.decision,
        justification=data.justification,
        conditions=data.conditions,
        idempotency_key=idempotency_key,
    )


@router.get(
    "/projects/{project_id}/approval",
    response_model=HumanApprovalStatusResponse,
)
def get_human_approval(
    project_id: Annotated[UUID, Path()],
    _: Annotated[dict[str, Any], Depends(require_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
) -> dict[str, Any]:
    return service.get_human_approval(project_id)

@router.post(
    "/projects/{project_id}/social-assessment",
    response_model=SocialAccessibilityResponse,
    status_code=status.HTTP_200_OK,
    summary="Evalúa la accesibilidad territorial en salud, educación y transporte (HU1.4)",
)
def evaluate_social_assessment(
    project_id: Annotated[UUID, Path()],
    user: Annotated[dict[str, Any], Depends(require_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", max_length=120)
    ] = None,
) -> dict[str, Any]:
    return service.evaluate_social_accessibility(
        project_id=project_id,
        actor_id=UUID(user["sub"]),
        idempotency_key=idempotency_key,
    )


@router.get(
    "/projects/{project_id}/social-assessment",
    response_model=SocialAccessibilityResponse,
    summary="Consulta la accesibilidad social territorial del proyecto (HU1.4)",
)
def get_social_assessment(
    project_id: Annotated[UUID, Path()],
    _: Annotated[dict[str, Any], Depends(require_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
) -> dict[str, Any]:
    return service.get_social_accessibility(project_id=project_id)

@router.post(
    "/projects/{project_id}/environmental-assessment",
    response_model=EnvironmentalAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Evalúa el impacto ambiental territorial de la obra (HU1.6)",
)
def evaluate_environmental_assessment(
    project_id: Annotated[UUID, Path()],
    user: Annotated[dict[str, Any], Depends(require_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", max_length=120)
    ] = None,
) -> dict[str, Any]:
    return service.evaluate_environmental_assessment(
        project_id=project_id,
        actor_id=UUID(user["sub"]),
        idempotency_key=idempotency_key,
    )


@router.get(
    "/projects/{project_id}/environmental-assessment",
    response_model=EnvironmentalAssessmentResponse,
    summary="Consulta la evaluación de impacto ambiental territorial del proyecto (HU1.6)",
)
def get_environmental_assessment(
    project_id: Annotated[UUID, Path()],
    _: Annotated[dict[str, Any], Depends(require_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
) -> dict[str, Any]:
    return service.get_environmental_assessment(project_id=project_id)

@router.post(
    "/projects/{project_id}/pert-estimate",
    response_model=PertEstimateResponse,
    status_code=status.HTTP_200_OK,
    summary="Registra o actualiza la estimación de duración de obra e incertidumbre PERT (HU1.9)",
)
def register_pert_estimate(
    project_id: Annotated[UUID, Path()],
    data: PertEstimateCreate,
    user: Annotated[dict[str, Any], Depends(require_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
) -> dict[str, Any]:
    return service.register_pert_estimate(
        project_id=project_id,
        actor_id=UUID(user["sub"]),
        data=data,
    )


@router.get(
    "/projects/{project_id}/pert-estimate",
    response_model=PertEstimateResponse | None,
    summary="Consulta la estimación de duración de obra e incertidumbre PERT del proyecto (HU1.9)",
)
def get_pert_estimate(
    project_id: Annotated[UUID, Path()],
    _: Annotated[dict[str, Any], Depends(require_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
) -> dict[str, Any] | None:
    return service.get_pert_estimate(project_id=project_id)

@router.post(
    "/projects/{project_id}/technical-assessment",
    response_model=TechnicalFeasibilityResponse,
    status_code=status.HTTP_200_OK,
    summary="Ejecuta y registra la preevaluación de viabilidad técnica del expediente (HU1.8)",
)
def evaluate_technical_feasibility(
    project_id: Annotated[UUID, Path()],
    user: Annotated[dict[str, Any], Depends(require_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any]:
    return service.evaluate_technical_feasibility(
        project_id=project_id,
        actor_id=UUID(user["sub"]),
        idempotency_key=idempotency_key,
    )


@router.get(
    "/projects/{project_id}/technical-assessment",
    response_model=TechnicalFeasibilityResponse | None,
    summary="Consulta la preevaluación de viabilidad técnica del expediente (HU1.8)",
)
def get_technical_feasibility(
    project_id: Annotated[UUID, Path()],
    _: Annotated[dict[str, Any], Depends(require_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
    version_id: Annotated[UUID | None, Query()] = None,
) -> dict[str, Any] | None:
    return service.get_technical_feasibility(project_id=project_id, version_id=version_id)

@router.get(
    "/projects/{project_id}/unified-summary",
    response_model=UnifiedAssessmentSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener resumen unificado de evaluacion multidimensional (HU1.12)",
    tags=["Evaluaciones"],
)
def get_unified_assessment_summary(
    project_id: Annotated[UUID, Path()],
    _: Annotated[dict[str, Any], Depends(require_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
    version_id: Annotated[UUID | None, Query()] = None,
) -> dict[str, Any]:
    return service.get_unified_assessment_summary(project_id=project_id, version_id=version_id)

