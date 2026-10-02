from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Path, status

from backend.application.dto.pmv1_dto import (
    EvaluationAccepted,
    EvaluationCreate,
    EvaluationResponse,
    HumanApprovalCreate,
    HumanApprovalResponse,
    HumanApprovalStatusResponse,
    LegalPrecheckResponse,
    LoginRequest,
    LoginResponse,
    NormativeDocumentListResponse,
    NormativeSearchRequest,
    NormativeSearchResponse,
    PMV1ProjectCreate,
    PMV1ProjectResponse,
    PMV1ValidationResponse,
    ZoningPrecheckResponse,
)
from backend.application.services.pmv1_services import AuthService, PlatformService
from backend.infrastructure.config.dependencies import (
    get_auth_service,
    get_platform_service,
    require_admin,
    require_legal_advisor,
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


@router.get("/projects/{project_id}", response_model=PMV1ProjectResponse)
def get_project(
    project_id: Annotated[UUID, Path()],
    _: Annotated[dict[str, Any], Depends(require_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
) -> dict[str, Any]:
    return service.get_project(project_id)


@router.post("/projects/{project_id}/validate", response_model=PMV1ValidationResponse)
def validate_project(
    project_id: Annotated[UUID, Path()],
    _: Annotated[dict[str, Any], Depends(require_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
) -> dict[str, Any]:
    return service.validate_project(project_id)


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
    user: Annotated[dict[str, Any], Depends(require_planner)],
    service: Annotated[PlatformService, Depends(get_platform_service)],
) -> dict[str, Any]:
    service.record_legal_abstention(project_id, UUID(user["sub"]))
    return {"project_id": project_id}


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
