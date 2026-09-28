from collections.abc import Awaitable, Callable
from typing import Any, NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.domain.entities.dictamen_ia import DictamenIA


class EvaluationState(TypedDict):
    proyecto: dict[str, Any]
    analisis_coordinador: NotRequired[str]
    analisis_tecnico: NotRequired[str]
    dictamen: NotRequired[DictamenIA]


GenerateDictamen = Callable[[dict[str, Any]], Awaitable[DictamenIA]]


async def coordinator_node(state: EvaluationState) -> dict[str, str]:
    proyecto = state["proyecto"]
    requeridos = (
        "nombre",
        "descripcion",
        "ubicacion",
        "presupuesto",
        "beneficiarios",
        "tipo_proyecto",
    )
    if any(proyecto.get(campo) in (None, "") for campo in requeridos):
        raise ValueError("Proyecto incompleto")
    return {
        "analisis_coordinador": (
            "Ficha minima completa. Evaluar coherencia entre necesidad, alcance, "
            "ubicacion, presupuesto, beneficiarios y tipo de proyecto. El resultado "
            "es preliminar y no constituye aprobacion municipal."
        )
    }


async def technical_node(state: EvaluationState) -> dict[str, str]:
    proyecto = state["proyecto"]
    presupuesto = float(proyecto["presupuesto"])
    beneficiarios = int(proyecto["beneficiarios"])
    if presupuesto <= 0 or beneficiarios <= 0:
        raise ValueError("Magnitudes no positivas")
    return {
        "analisis_tecnico": (
            f"Presupuesto declarado: S/ {presupuesto:.2f}; beneficiarios: "
            f"{beneficiarios}; costo declarado por beneficiario: "
            f"S/ {presupuesto / beneficiarios:.2f}. Este cociente no demuestra "
            "rentabilidad. No se verificaron metrados, cronograma, costos unitarios "
            "ni expediente tecnico; el dictamen debe explicitar estas limitaciones."
        )
    }


def build_evaluation_graph(generate: GenerateDictamen):
    async def consolidate(state: EvaluationState) -> dict[str, DictamenIA]:
        contexto = {
            "proyecto": state["proyecto"],
            "analisis_coordinador": state["analisis_coordinador"],
            "analisis_tecnico": state["analisis_tecnico"],
        }
        return {"dictamen": await generate(contexto)}

    graph = StateGraph(EvaluationState)
    graph.add_node("coordinador", coordinator_node)
    graph.add_node("tecnico", technical_node)
    graph.add_node("dictamen", consolidate)
    graph.add_edge(START, "coordinador")
    graph.add_edge("coordinador", "tecnico")
    graph.add_edge("tecnico", "dictamen")
    graph.add_edge("dictamen", END)
    return graph.compile()
