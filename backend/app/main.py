from fastapi import FastAPI
from app.infrastructure.config.settings import get_settings
from app.infrastructure.input.controllers.evaluaciones import router as evaluaciones_router
from app.infrastructure.input.controllers.proyectos import router as proyectos_router

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")

app.include_router(proyectos_router)
app.include_router(evaluaciones_router)


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
