from app.ai.graph.state import EvaluationState


async def technical_node(state: EvaluationState) -> EvaluationState:
    proyecto = state.get("proyecto", {})
    presupuesto = proyecto.get("presupuesto", 0)
    beneficiarios = proyecto.get("poblacion_beneficiaria", 0)
    return {
        **state,
        "analisis_tecnico": (
            f"Analisis tecnico preliminar: presupuesto={presupuesto}, "
            f"beneficiarios={beneficiarios}. Requiere validacion documental en PMV2."
        ),
    }
