class CredencialesInvalidasError(Exception):
    pass


class AccesoDenegadoError(Exception):
    pass


class RecursoPMV1NoEncontradoError(Exception):
    pass


class ExpedientePMV1IncompletoError(Exception):
    def __init__(self, campos_faltantes: list[str]) -> None:
        self.campos_faltantes = campos_faltantes
        super().__init__(
            "El expediente esta incompleto: " + ", ".join(campos_faltantes)
        )


class ConfiguracionPMV1Error(Exception):
    pass


class ServicioNoDisponibleError(Exception):
    """Error controlado cuando un servicio de base de datos o infraestructura no responde."""
    pass

class EstimacionPERTInvalidaError(Exception):
    """Error cuando los parámetros de duración PERT están incompletos, no son finitos o no cumplen 0 <= a <= m <= b."""

    def __init__(
        self,
        mensaje: str,
        campo: str | None = None,
        motivo: str | None = None,
    ) -> None:
        self.campo = campo
        self.motivo = motivo
        super().__init__(mensaje)


class VersionNoPertenecienteError(Exception):
    """Error cuando el project_version_id proporcionado no pertenece al project_id de la URL."""

    def __init__(
        self,
        mensaje: str,
        project_id: str | None = None,
        version_id: str | None = None,
    ) -> None:
        self.project_id = project_id
        self.version_id = version_id
        super().__init__(mensaje)
