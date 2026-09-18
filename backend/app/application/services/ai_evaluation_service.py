from typing import Any, Mapping
from app.ai.graph.evaluation_graph import build_evaluation_graph
from app.domain.ports.ia_service import IIAService


class AIEvaluationService(IIAService):
    """Ejecuta el grafo mínimo y delega la generación final al proveedor LLM."""

    def __init__(self, llm_service: IIAService) -> None:
        self.llm_service = llm_service
        self.graph = build_evaluation_graph()

    async def generar_dictamen(self, proyecto: Mapping[str, Any]) -> dict[str, Any]:
        state = await self.graph.ainvoke({"proyecto": dict(proyecto)})
        contexto = {
            **dict(proyecto),
            "analisis_coordinador": state.get("analisis_coordinador"),
            "analisis_tecnico": state.get("analisis_tecnico"),
        }
        return await self.llm_service.generar_dictamen(contexto)
