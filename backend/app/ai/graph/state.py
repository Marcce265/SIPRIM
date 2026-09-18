from typing import Any, TypedDict


class EvaluationState(TypedDict, total=False):
    proyecto: dict[str, Any]
    analisis_coordinador: str
    analisis_tecnico: str
    dictamen: dict[str, Any]
