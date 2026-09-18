from app.ai.graph.state import EvaluationState


async def technical_node(state: EvaluationState) -> dict[str, str]:
    proyecto = state["proyecto"]
    presupuesto = float(proyecto["presupuesto"])
    beneficiarios = int(proyecto["poblacion_beneficiaria"])
    if presupuesto <= 0 or beneficiarios <= 0:
        raise ValueError("Magnitudes no positivas")
    return {"analisis_tecnico": (
        f"Presupuesto declarado: S/ {presupuesto:.2f}; "
        f"población beneficiaria: {beneficiarios}; "
        f"costo declarado por beneficiario: S/ {presupuesto / beneficiarios:.2f}. "
        "Este cociente no demuestra rentabilidad ni viabilidad. No se han "
        "verificado expediente técnico, metrados, cronograma ni costos unitarios. "
        "La consolidación debe indicar incertidumbres y documentos faltantes."
    )}
