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
