from app.ai.graph.state import EvaluationState


async def coordinator_node(state: EvaluationState) -> EvaluationState:
    proyecto = state.get("proyecto", {})
    return {
        **state,
        "analisis_coordinador": (
            f"Proyecto '{proyecto.get('nombre', 'sin nombre')}' recibido y preparado "
            "para evaluacion multiagente."
        ),
    }
