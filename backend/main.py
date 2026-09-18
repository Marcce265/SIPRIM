from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.domain.exceptions.proyecto_exceptions import (
    ProyectoInvalidoError,
    ProyectoNoEncontradoError,
)
from backend.infrastructure.config.settings import get_settings
from backend.infrastructure.input.controllers.proyecto_controller import (
    router as proyecto_router,
)


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="API del PMV1 para priorizacion de proyectos urbanos.",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(proyecto_router)

    @application.get("/health", tags=["Sistema"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.exception_handler(ProyectoNoEncontradoError)
    async def proyecto_no_encontrado_handler(
        request: Request, exc: ProyectoNoEncontradoError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @application.exception_handler(ProyectoInvalidoError)
    async def proyecto_invalido_handler(
        request: Request, exc: ProyectoInvalidoError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(exc)},
        )

    return application


app = create_app()
