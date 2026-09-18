from app.application.schemas.proyecto import ProyectoCreate, ProyectoResponse


class RegistrarProyecto:
    """Caso de uso temporal en memoria para demostrar el PMV.

    El repositorio PostgreSQL se conectará cuando el módulo de persistencia del grupo
    esté disponible.
    """

    _secuencia = 0

    async def ejecutar(self, datos: ProyectoCreate) -> ProyectoResponse:
        type(self)._secuencia += 1
        return ProyectoResponse(id=self._secuencia, **datos.model_dump())
