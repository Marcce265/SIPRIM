from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.application.services.pmv1_services import AuthService, PlatformService
from backend.application.use_cases.evaluar_cumplimiento_legal import (
    EvaluarCumplimientoLegalUseCase,
)
from backend.application.use_cases.evaluar_economia_proyecto import (
    EvaluarEconomiaProyectoUseCase,
)
from backend.application.use_cases.evaluar_proyecto_ia import EvaluarProyectoIAUseCase
from backend.application.use_cases.obtener_proyecto import ObtenerProyectoUseCase
from backend.application.use_cases.registrar_proyecto import RegistrarProyectoUseCase
from backend.application.use_cases.validar_proyecto import ValidarProyectoUseCase
from backend.domain.exceptions.pmv1_exceptions import AccesoDenegadoError
from backend.domain.ports.evaluacion_economica_repository_port import (
    EvaluacionEconomicaRepositoryPort,
)
from backend.domain.ports.evaluacion_juridica_port import EvaluacionJuridicaPort
from backend.domain.ports.evaluacion_juridica_repository_port import (
    EvaluacionJuridicaRepositoryPort,
)
from backend.domain.ports.ia_service_port import IAServicePort
from backend.domain.ports.proyecto_repository_port import ProyectoRepositoryPort
from backend.infrastructure.config.settings import get_settings
from backend.infrastructure.output.broker.celery_app import CeleryTaskDispatcher
from backend.infrastructure.output.legal.evaluacion_juridica_provisional_adapter import (
    EvaluacionJuridicaProvisionalAdapter,
)
from backend.infrastructure.output.repositories.in_memory_evaluacion_economica_repository import (
    InMemoryEvaluacionEconomicaRepository,
)
from backend.infrastructure.output.repositories.in_memory_evaluacion_juridica_repository import (
    InMemoryEvaluacionJuridicaRepository,
)
from backend.infrastructure.output.repositories.in_memory_proyecto_repository import (
    InMemoryProyectoRepository,
)


@lru_cache
def get_proyecto_repository() -> ProyectoRepositoryPort:
    """Punto unico donde se elige el adaptador de persistencia."""

    if get_settings().use_in_memory_repository:
        return InMemoryProyectoRepository()

    # Importacion diferida: PostgreSQL solo se prepara si el adaptador esta activo.
    from backend.infrastructure.output.database.session import SessionLocal
    from backend.infrastructure.output.repositories.sqlalchemy_proyecto_repository import (
        SQLAlchemyProyectoRepository,
    )

    return SQLAlchemyProyectoRepository(SessionLocal)


@lru_cache
def get_evaluacion_economica_repository() -> EvaluacionEconomicaRepositoryPort:
    if get_settings().use_in_memory_repository:
        return InMemoryEvaluacionEconomicaRepository()

    from backend.infrastructure.output.database.session import SessionLocal
    from backend.infrastructure.output.repositories.sqlalchemy_evaluacion_economica_repository import (
        SQLAlchemyEvaluacionEconomicaRepository,
    )

    return SQLAlchemyEvaluacionEconomicaRepository(SessionLocal)


@lru_cache
def get_evaluador_juridico() -> EvaluacionJuridicaPort:
    return EvaluacionJuridicaProvisionalAdapter()


@lru_cache
def get_evaluacion_juridica_repository() -> EvaluacionJuridicaRepositoryPort:
    if get_settings().use_in_memory_repository:
        return InMemoryEvaluacionJuridicaRepository()

    from backend.infrastructure.output.database.session import SessionLocal
    from backend.infrastructure.output.repositories.sqlalchemy_evaluacion_juridica_repository import (
        SQLAlchemyEvaluacionJuridicaRepository,
    )

    return SQLAlchemyEvaluacionJuridicaRepository(SessionLocal)


@lru_cache
def get_ia_service() -> IAServicePort:
    # Gemini es una integracion opcional. Importarlo aqui evita que la API base y
    # sus pruebas fallen al arrancar cuando el extra de IA no esta instalado.
    from backend.infrastructure.output.ai.gemini_adapter import GeminiAdapter

    settings = get_settings()
    api_key = (
        settings.gemini_api_key.get_secret_value()
        if settings.gemini_api_key
        else None
    )
    return GeminiAdapter(
        api_key=api_key,
        model=settings.ai_model,
        timeout_seconds=settings.ai_timeout_seconds,
    )


def get_registrar_proyecto_use_case(
    repository: ProyectoRepositoryPort = Depends(get_proyecto_repository),
) -> RegistrarProyectoUseCase:
    return RegistrarProyectoUseCase(repository)


def get_obtener_proyecto_use_case(
    repository: ProyectoRepositoryPort = Depends(get_proyecto_repository),
) -> ObtenerProyectoUseCase:
    return ObtenerProyectoUseCase(repository)


def get_validar_proyecto_use_case(
    repository: ProyectoRepositoryPort = Depends(get_proyecto_repository),
) -> ValidarProyectoUseCase:
    return ValidarProyectoUseCase(repository)


def get_evaluar_economia_proyecto_use_case(
    proyecto_repository: ProyectoRepositoryPort = Depends(get_proyecto_repository),
    evaluacion_repository: EvaluacionEconomicaRepositoryPort = Depends(
        get_evaluacion_economica_repository
    ),
) -> EvaluarEconomiaProyectoUseCase:
    return EvaluarEconomiaProyectoUseCase(
        proyecto_repository=proyecto_repository,
        evaluacion_repository=evaluacion_repository,
    )


def get_evaluar_cumplimiento_legal_use_case(
    proyecto_repository: ProyectoRepositoryPort = Depends(get_proyecto_repository),
    evaluador_juridico: EvaluacionJuridicaPort = Depends(get_evaluador_juridico),
    evaluacion_repository: EvaluacionJuridicaRepositoryPort = Depends(
        get_evaluacion_juridica_repository
    ),
) -> EvaluarCumplimientoLegalUseCase:
    return EvaluarCumplimientoLegalUseCase(
        proyecto_repository=proyecto_repository,
        evaluador_juridico=evaluador_juridico,
        evaluacion_repository=evaluacion_repository,
    )


def get_evaluar_proyecto_ia_use_case(
    proyecto_repository: ProyectoRepositoryPort = Depends(get_proyecto_repository),
    ia_service: IAServicePort = Depends(get_ia_service),
) -> EvaluarProyectoIAUseCase:
    return EvaluarProyectoIAUseCase(
        proyecto_repository=proyecto_repository,
        ia_service=ia_service,
    )


@lru_cache
def get_auth_service() -> AuthService:
    settings = get_settings()
    return AuthService(
        settings.auth_db_url,
        settings.jwt_secret.get_secret_value(),
        settings.jwt_issuer,
        settings.jwt_audience,
        settings.jwt_expiration_minutes,
    )


@lru_cache
def get_platform_service() -> PlatformService:
    settings = get_settings()
    return PlatformService(settings.platform_db_url, CeleryTaskDispatcher())


bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        from backend.domain.exceptions.pmv1_exceptions import CredencialesInvalidasError

        raise CredencialesInvalidasError("Autenticacion requerida")
    return auth.decode(credentials.credentials)


def _user_roles(user: dict[str, Any]) -> list[str]:
    return list(user.get("roles", []))


def _is_superadmin(roles: list[str]) -> bool:
    return "SUPERADMIN" in roles


def require_planner(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    roles = _user_roles(user)
    if _is_superadmin(roles) or "PLANNER" in roles:
        return user
    raise AccesoDenegadoError("Se requiere el rol PLANNER")


def require_legal_advisor(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    roles = _user_roles(user)
    if _is_superadmin(roles) or "LEGAL_ADVISOR" in roles or "ADMIN" in roles:
        return user
    raise AccesoDenegadoError("Se requiere el rol LEGAL_ADVISOR o ADMIN")


def require_admin(
    user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    roles = _user_roles(user)
    if _is_superadmin(roles) or "ADMIN" in roles:
        return user
    raise AccesoDenegadoError("Se requiere el rol ADMIN")
