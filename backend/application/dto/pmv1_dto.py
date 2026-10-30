from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LoginRequest(BaseModel):
    email: str = Field(
        min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    )
    password: str = Field(min_length=8, max_length=200)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: UUID
    full_name: str
    roles: list[str]


class PMV1ProjectCreate(BaseModel):
    """Expediente mínimo persistido por ms-platform según el PMV1."""

    model_config = ConfigDict(extra="forbid")
    code: str | None = Field(
        default=None, min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_-]+$"
    )
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    location: str | None = Field(default=None, max_length=300)
    proposed_land_use: str | None = Field(default=None, max_length=150)
    estimated_budget_pen: Decimal | None = Field(
        default=None, max_digits=18, decimal_places=2
    )
    beneficiaries_count: int | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else value

    @field_validator(
        "title", "description", "location", "proposed_land_use", mode="before"
    )
    @classmethod
    def strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value


class PMV1ProjectResponse(BaseModel):
    project_id: UUID
    project_version_id: UUID
    code: str
    version_number: int
    status: str
    title: str
    description: str
    location: str | None
    proposed_land_use: str | None
    territorial_data_origin: str
    estimated_budget_pen: Decimal
    beneficiaries_count: int


class PMV1ValidationResponse(BaseModel):
    complete: bool
    status: str
    missing_fields: list[str]
    message: str


class EvaluationCreate(BaseModel):
    project_version_id: UUID


class EvaluationAccepted(BaseModel):
    evaluation_id: UUID
    event_id: UUID
    status: str
    duplicated: bool
    publication_pending: bool


class EconomicResult(BaseModel):
    economic_assessment_id: UUID
    cost_per_beneficiary_pen: Decimal
    score_0_100: Decimal
    explanation: str
    algorithm_version: str
    socioeconomic_return: None = None
    warnings: list[str] = [
        "No se calcula retorno socioeconomico sin beneficios monetizados y trazables."
    ]


class EvaluationResponse(BaseModel):
    evaluation_id: UUID
    project_version_id: UUID
    criteria_version_id: UUID
    status: str
    result: EconomicResult | None


class LegalPrecheckResponse(BaseModel):
    project_id: UUID
    status: str = "requires_review"
    complies: bool | None = None
    sources: list[str] = []
    requires_review: bool = True
    observations: list[str] = [
        "El PMV1 no contiene un corpus normativo versionado para emitir un dictamen de la Ley de Contrataciones.",
        "Se requiere revision de un asesor juridico; el sistema se abstiene de afirmar cumplimiento.",
    ]
    assessment: "LegalAssessmentResponse | None" = None
    findings: list["LegalFindingItem"] = []


class ZoningEvidence(BaseModel):
    document: str
    version: str
    locator: str
    excerpt: str


class ZoningPrecheckResponse(BaseModel):
    review_id: UUID
    project_id: UUID
    project_version_id: UUID
    status: str
    compatible: bool | None
    location: str
    proposed_land_use: str
    territorial_data_origin: str
    evidence: list[ZoningEvidence]
    alerts: list[str]
    limitations: str
    requires_human_review: bool
    duplicated: bool


class NormativeSearchRequest(BaseModel):
    """Solicitud de busqueda automatica en normativas vigentes (HU2.1 / RF12)."""

    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=2, max_length=500)
    document_filter: str | None = Field(default=None, max_length=150)
    only_in_force: bool = True
    limit: int = Field(default=5, ge=1, le=20)

    @field_validator("query", "document_filter", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return value


class NormativeChunkItem(BaseModel):
    """Fragmento normativo recuperado con trazabilidad de origen y metadatos."""

    id: str
    document_name: str
    short_code: str
    version: str
    topic: str
    content: str
    in_force: bool
    has_alert: bool
    data_origin: str
    relevance_score: float
    location: str | None = None


class NormativeSearchResponse(BaseModel):
    """Resultado de busqueda normativa para el Asesor Juridico (HU2.1)."""

    query: str
    document_filter: str | None
    total_results: int
    results: list[NormativeChunkItem]
    alerts_found: list[str]
    disclaimer: str
    requires_human_review: bool
    duplicated: bool = False


class NormativeDocumentItem(BaseModel):
    """Resumen de norma o plan territorial registrado en el catalogo."""

    short_code: str
    document_name: str
    version: str
    in_force: bool
    data_origin: str
    chunks_count: int


class NormativeDocumentListResponse(BaseModel):
    """Listado del catalogo normativo activo y versionado (RF03)."""

    total_documents: int
    documents: list[NormativeDocumentItem]
    disclaimer: str


class HumanApprovalCreate(BaseModel):
    """Solicitud de dictamen humano formal (aprobacion, rechazo u observacion)."""

    model_config = ConfigDict(extra="forbid")
    decision: Literal["approved", "rejected", "observed"]
    justification: str = Field(min_length=5, max_length=2000)
    conditions: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_conditions_when_observed(self) -> "HumanApprovalCreate":
        if self.decision == "observed" and (self.conditions is None or not self.conditions.strip()):
            raise ValueError("El dictamen 'observed' requiere especificar condiciones u observaciones")
        if self.conditions is not None:
            self.conditions = self.conditions.strip() if self.conditions.strip() else None
        return self


class HumanApprovalResponse(BaseModel):
    """Dictamen humano formal registrado para un proyecto."""

    approval_id: UUID
    project_id: UUID
    project_version_id: UUID
    decision: str
    justification: str
    conditions: str | None = None
    decided_by_user_id: UUID
    idempotency_key: str
    decided_at: datetime
    duplicated: bool = False


class HumanApprovalStatusResponse(BaseModel):
    """Estado de compuerta humana formal y dictamen actual del proyecto."""

    project_id: UUID
    project_version_id: UUID
    project_status: str
    is_evaluated: bool
    requires_human_approval: bool
    current_approval: HumanApprovalResponse | None = None

class SocialAccessibilityCategoryItem(BaseModel):
    category: str
    category_label: str
    status: str
    has_sufficient_data: bool
    indicator: str | None = None
    value: float | None = None
    unit: str | None = None
    source: str
    data_origin: str
    is_simulated: bool = True
    message: str


class DemographicEquityDimensionItem(BaseModel):
    dimension: Literal["genero", "edad"]
    dimension_label: str
    target_group: str
    has_sufficient_data: bool
    aggregated_population: int | None = None
    aggregated_percentage: float | None = None
    equity_criterion: str
    declared_benefit: str | None = None
    verifiable_data: str | None = None
    has_favorable_evidence: bool = False
    score_effect_pts: float | None = None
    effect_type: Literal["favorable", "neutro", "desfavorable", "indeterminado"] = "indeterminado"
    effect_explanation: str
    source_name: str
    data_origin: str = "simulated"
    is_simulated: bool = True


class DemographicEquityItem(BaseModel):
    has_sufficient_data: bool
    gender: DemographicEquityDimensionItem
    age: DemographicEquityDimensionItem
    equity_score_pts: float | None = None
    effect_summary: str


class SocialAccessibilityResponse(BaseModel):
    project_id: UUID
    project_code: str
    project_version_id: UUID | None = None
    status: str
    summary: str
    categories: list[SocialAccessibilityCategoryItem]
    equity: DemographicEquityItem | None = None
    social_score: float | None = None
    score_explanation: str | None = None
    evaluated_at: datetime
    duplicated: bool = False

class EnvironmentalImpactItem(BaseModel):
    component: str
    component_label: str
    description: str
    severity: Literal["baja", "moderada", "alta", "indeterminada"]
    substantiation: str
    mitigations: list[str]


class EnvironmentalMitigationItem(BaseModel):
    component: str
    measure: str
    type: str
    origin: str


class EnvironmentalDeclaredVsEvidence(BaseModel):
    declared_by_applicant: str | None
    declared_measures: str | None
    verifiable_evidence: str | None
    evidence_source: str
    is_simulated: bool = True
    proximity_to_water_meters: float | None = None
    is_in_protected_or_risk_area: bool | None = None



class GreenAreaRecordItem(BaseModel):
    has_sufficient_data: bool = True
    total_project_area_m2: float | None = None
    green_area_m2: float | None = None
    green_area_percentage: float | None = None
    delimitation_description: str | None = None
    declared_affectation: str | None = None
    verifiable_affectation: str | None = None
    affectation_type: str | None = None
    affectation_type_label: str | None = None
    protection_measures: str | None = None
    has_sufficient_measures: bool = True
    score_effect_pts: float | None = None
    effect_type: Literal["bonus", "penalizacion", "neutro", "indeterminado"] = "indeterminado"
    calculation_explanation: str
    source_name: str
    data_origin: str = "simulated"
    is_simulated: bool = True

class EnvironmentalAssessmentResponse(BaseModel):
    project_id: UUID
    project_code: str
    project_version_id: UUID | None = None
    status: Literal["sufficient", "insufficient"]
    risk_level: Literal["low", "moderate", "high", "insufficient"]
    risk_level_label: str
    risk_observation: str | None = None
    requires_human_review: bool
    favorable: bool | None = None
    favorable_label: str
    summary: str
    declared_vs_evidence: EnvironmentalDeclaredVsEvidence
    impacts: list[EnvironmentalImpactItem]
    mitigations: list[EnvironmentalMitigationItem]
    green_area: GreenAreaRecordItem | None = None
    environmental_score: float | None = None
    score_explanation: str | None = None
    evaluated_at: datetime
    duplicated: bool = False

# =========================================================
# PMV 2 - HU2.2: Citas Jurídicas Verificables
# =========================================================
class NormativeCitationItem(BaseModel):
    fragment_id: str | None = None
    document_name: str | None = None
    short_code: str | None = None
    version: str | None = None
    article_or_section: str | None = None
    fragment_content: str | None = None
    citation_status: Literal["verificable", "no_verificable"]
    is_verifiable: bool
    status_label: str
    limitation_note: str | None = None
    in_force: bool = True
    is_simulated: bool = False
    data_origin: str = "public"
    citation_hash: str | None = None


class LegalFindingItem(BaseModel):
    finding_id: UUID
    finding_key: str
    title: str
    description: str
    complies: bool | None = None
    requires_human_review: bool = True
    citation: NormativeCitationItem


class LegalAssessmentResponse(BaseModel):
    assessment_id: UUID
    project_id: UUID
    project_code: str
    project_version_id: UUID | None = None
    status: Literal["requires_review", "verified", "insufficient"]
    status_label: str
    summary: str
    findings: list[LegalFindingItem]
    total_findings: int
    verifiable_citations_count: int
    unverifiable_citations_count: int
    requires_human_review: bool
    evaluated_at: datetime
    is_simulated_corpus: bool = True
    duplicated: bool = False

