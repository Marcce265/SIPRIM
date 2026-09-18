"""Errores independientes del transporte HTTP y del proveedor."""


class IAError(Exception):
    code = "IA_ERROR"
    message = "No se pudo completar la evaluación IA."

    def __init__(self):
        super().__init__(self.message)


class IAConfigurationError(IAError):
    code = "IA_NOT_CONFIGURED"
    message = "El servicio IA no está configurado."


class IAAuthenticationError(IAError):
    code = "IA_AUTH_ERROR"
    message = "El proveedor rechazó las credenciales del servicio IA."


class IATimeoutError(IAError):
    code = "IA_TIMEOUT"
    message = "El servicio IA excedió el tiempo de espera."


class IARateLimitError(IAError):
    code = "IA_RATE_LIMIT"
    message = "Se alcanzó la cuota del servicio IA. Intente más tarde."


class IAProviderError(IAError):
    code = "IA_PROVIDER_ERROR"
    message = "El proveedor IA no pudo completar la solicitud."


class IAInvalidResponseError(IAError):
    code = "IA_INVALID_RESPONSE"
    message = "El proveedor IA devolvió un dictamen inválido."


class IAEmptyResponseError(IAError):
    code = "IA_EMPTY_RESPONSE"
    message = "El proveedor IA no devolvió un dictamen."


class IAGraphError(IAError):
    code = "IA_GRAPH_ERROR"
    message = "No se pudo completar el flujo de evaluación."
