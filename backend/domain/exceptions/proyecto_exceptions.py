class ProyectoError(Exception):
    """Excepcion base del agregado Proyecto."""


class ProyectoInvalidoError(ProyectoError):
    """Se produce cuando se intenta crear un proyecto inconsistente."""


class ProyectoNoEncontradoError(ProyectoError):
    def __init__(self, proyecto_id: int) -> None:
        super().__init__(f"No se encontro el proyecto con id {proyecto_id}")


class ExpedienteIncompletoError(ProyectoError):
    def __init__(self, proyecto_id: int, campos_faltantes: list[str]) -> None:
        self.proyecto_id = proyecto_id
        self.campos_faltantes = campos_faltantes
        super().__init__(
            f"El proyecto {proyecto_id} tiene un expediente incompleto y no puede evaluarse"
        )

