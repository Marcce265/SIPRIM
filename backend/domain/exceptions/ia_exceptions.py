class IAError(Exception):
    code = "IA_ERROR"
    message = "No se pudo completar la evaluacion IA."

    def __init__(self) -> None:
        super().__init__(self.message)


class IAConfigurationError(IAError):
    code = "IA_NOT_CONFIGURED"
    message = "El servicio IA no esta configurado."


class IAAuthenticationError(IAError):
    code = "IA_AUTH_ERROR"
    message = "Gemini rechazo las credenciales del servicio."


class IATimeoutError(IAError):
    code = "IA_TIMEOUT"
    message = "El servicio IA excedio el tiempo de espera."


class IARateLimitError(IAError):
    code = "IA_RATE_LIMIT"
    message = "Se alcanzo la cuota de Gemini. Intente nuevamente mas tarde."


class IAProviderError(IAError):
    code = "IA_PROVIDER_ERROR"
    message = "Gemini no pudo completar la solicitud."


class IAInvalidResponseError(IAError):
    code = "IA_INVALID_RESPONSE"
    message = "Gemini devolvio un dictamen invalido."


class IAEmptyResponseError(IAError):
    code = "IA_EMPTY_RESPONSE"
    message = "Gemini no devolvio un dictamen."


class IAGraphError(IAError):
    code = "IA_GRAPH_ERROR"
    message = "No se pudo completar el flujo de evaluacion."
