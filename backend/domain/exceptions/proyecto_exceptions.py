class ProyectoError(Exception):
    """Excepcion base del agregado Proyecto."""


class ProyectoInvalidoError(ProyectoError):
    """Se produce cuando se intenta crear un proyecto inconsistente."""


class ProyectoNoEncontradoError(ProyectoError):
    def __init__(self, proyecto_id: int) -> None:
        super().__init__(f"No se encontro el proyecto con id {proyecto_id}")

