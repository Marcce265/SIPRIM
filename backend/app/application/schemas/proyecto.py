from pydantic import BaseModel, Field


class ProyectoCreate(BaseModel):
    nombre: str = Field(min_length=3, max_length=200)
    descripcion: str = Field(min_length=10)
    presupuesto: float = Field(gt=0, allow_inf_nan=False)
    poblacion_beneficiaria: int = Field(gt=0)
    distrito: str = Field(min_length=2, max_length=120)


class ProyectoResponse(ProyectoCreate):
    id: int
