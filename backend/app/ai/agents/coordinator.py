from app.ai.graph.state import EvaluationState


async def coordinator_node(state: EvaluationState) -> dict[str, str]:
    proyecto = state["proyecto"]
    faltantes = [campo for campo in (
        "nombre", "descripcion", "presupuesto", "poblacion_beneficiaria", "distrito"
    ) if not proyecto.get(campo)]
    if faltantes:
        raise ValueError("Proyecto incompleto")
    return {"analisis_coordinador": (
        "Ficha mínima completa. Evaluar coherencia del objetivo, alcance, "
        "presupuesto y beneficiarios. Alcance preliminar técnico; no emitir "
        "aprobación oficial ni conclusiones jurídicas, sociales o ambientales."
    )}
