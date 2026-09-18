from collections.abc import Awaitable, Callable
from typing import Any
from langgraph.graph import END, START, StateGraph
from app.ai.agents.coordinator import coordinator_node
from app.ai.agents.technical import technical_node
from app.ai.graph.state import EvaluationState
from app.domain.value_objects.dictamen_ia import DictamenIA

GenerateDictamen = Callable[[dict[str, Any]], Awaitable[DictamenIA]]


def build_evaluation_graph(generate: GenerateDictamen):
    async def consolidate(state: EvaluationState) -> dict[str, DictamenIA]:
        contexto = {
            "proyecto": state["proyecto"],
            "analisis_coordinador": state["analisis_coordinador"],
            "analisis_tecnico": state["analisis_tecnico"],
        }
        return {"dictamen": DictamenIA.model_validate(await generate(contexto))}

    graph = StateGraph(EvaluationState)
    graph.add_node("coordinador", coordinator_node)
    graph.add_node("tecnico", technical_node)
    graph.add_node("dictamen", consolidate)
    graph.add_edge(START, "coordinador")
    graph.add_edge("coordinador", "tecnico")
    graph.add_edge("tecnico", "dictamen")
    graph.add_edge("dictamen", END)
    return graph.compile()
