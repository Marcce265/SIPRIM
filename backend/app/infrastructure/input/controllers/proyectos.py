from fastapi import APIRouter
from app.application.schemas.proyecto import ProyectoCreate, ProyectoResponse
from app.application.use_cases.registrar_proyecto import RegistrarProyecto

router = APIRouter(prefix="/api/proyectos", tags=["Proyectos"])


@router.post("", response_model=ProyectoResponse, status_code=201)
async def registrar_proyecto(payload: ProyectoCreate) -> ProyectoResponse:
    return await RegistrarProyecto().ejecutar(payload)
