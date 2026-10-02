from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
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
    code: str | None = Field(default=None, min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    estimated_budget_pen: Decimal | None = Field(default=None, max_digits=18, decimal_places=2)
    beneficiaries_count: int | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else value

    @field_validator("title", "description", mode="before")
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
    complies: None = None
    sources: list[str] = []
    requires_review: bool = True
    observations: list[str] = [
        "El PMV1 no contiene un corpus normativo versionado para emitir un dictamen de la Ley de Contrataciones.",
        "Se requiere revision de un asesor juridico; el sistema se abstiene de afirmar cumplimiento.",
    ]
