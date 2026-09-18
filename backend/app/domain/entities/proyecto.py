from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class Proyecto:
    id: Optional[int]
    nombre: str
    descripcion: str
    presupuesto: float
    poblacion_beneficiaria: int
    distrito: str
