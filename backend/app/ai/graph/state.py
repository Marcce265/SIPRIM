from typing import Any, NotRequired, TypedDict
from app.domain.value_objects.dictamen_ia import DictamenIA


class EvaluationState(TypedDict):
    proyecto: dict[str, Any]
    analisis_coordinador: NotRequired[str]
    analisis_tecnico: NotRequired[str]
    dictamen: NotRequired[DictamenIA]
