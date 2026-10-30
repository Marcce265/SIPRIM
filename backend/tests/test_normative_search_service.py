from backend.application.services.pmv1_services import (
    NormativeSearchEngine,
    _load_fallback_seed_documents,
)


def test_keywords_extraction_and_stop_words():
    query = "El plan de desarrollo urbano y la zonificación de suelo en Huancayo"
    keywords = NormativeSearchEngine.extract_keywords(query)
    # Stop words must be filtered out
    assert "el" not in keywords
    assert "de" not in keywords
    assert "y" not in keywords
    assert "la" not in keywords
    assert "en" not in keywords
    # Key tokens must be preserved
    assert "plan" in keywords
    assert "desarrollo" in keywords
    assert "urbano" in keywords
    assert "zonificación" in keywords
    assert "suelo" in keywords
    assert "huancayo" in keywords


def test_score_chunk_exact_id_match():
    chunk = {
        "id": "PDUPDM-02",
        "document_name": "PDU/PDM Huancayo-El Tambo",
        "short_code": "PDU_EL_TAMBO",
        "topic": "Compatibilidad de uso de suelo",
        "content": "si el uso propuesto es incompatible requiere observacion",
        "has_alert": True,
    }
    keywords = NormativeSearchEngine.extract_keywords("PDUPDM-02")
    score = NormativeSearchEngine.score_chunk(chunk, "PDUPDM-02", keywords)
    assert score >= 50.0


def test_score_chunk_alert_boosting():
    alert_chunk = {
        "id": "PDUPDM-04",
        "document_name": "PDU/PDM Huancayo-El Tambo",
        "short_code": "PDU_EL_TAMBO",
        "topic": "Zonas de riesgo",
        "content": "propuesta ubicada en area de riesgo alto no mitigable",
        "has_alert": True,
    }
    non_alert_chunk = {
        "id": "PDUPDM-05",
        "document_name": "PDU/PDM Huancayo-El Tambo",
        "short_code": "PDU_EL_TAMBO",
        "topic": "Sistema vial",
        "content": "red vial y movilidad",
        "has_alert": False,
    }
    query = "proyecto en zona de riesgo alto"
    kw = NormativeSearchEngine.extract_keywords(query)
    score_alert = NormativeSearchEngine.score_chunk(alert_chunk, query, kw)
    score_non_alert = NormativeSearchEngine.score_chunk(non_alert_chunk, query, kw)
    assert score_alert > score_non_alert
    assert score_alert >= 50.0


def test_score_chunk_no_match():
    chunk = {
        "id": "DL1252-01",
        "document_name": "D. L. N.° 1252 - Invierte.pe",
        "short_code": "DL_1252",
        "topic": "Programación multianual",
        "content": "cierre de brechas prioritarias",
        "has_alert": False,
    }
    query = "arquitectura hospitalaria neonatologia"
    kw = NormativeSearchEngine.extract_keywords(query)
    score = NormativeSearchEngine.score_chunk(chunk, query, kw)
    assert score == 0.0


# === HU2.1 Acceptance Criteria Verification Tests ===


def test_hu21_ca1_resolve_location_identifiable():
    """CA-HU2.1-01: Ubicacion identificable del fragmento (articulo, seccion o ID estable)."""
    # 1. Extrae de parentesis en topic
    chunk_topic = {
        "id": "LEY27972-01",
        "topic": "Competencias municipales (Art. 73)",
        "content": "Las municipalidades ejercen competencias...",
    }
    loc1 = NormativeSearchEngine.resolve_location(chunk_topic)
    assert loc1 == "Art. 73"

    # 2. Extrae de seccion/titulo en topic
    chunk_title = {
        "id": "PDUPDM-02",
        "topic": "Zonificación urbana (Título III del Reglamento de Zonificación)",
        "content": "Compatibilidad de usos...",
    }
    loc2 = NormativeSearchEngine.resolve_location(chunk_title)
    assert "Título III" in loc2

    # 3. Extrae de articulo al inicio del contenido
    chunk_content = {
        "id": "CUSTOM-01",
        "topic": "Disposiciones generales",
        "content": "Art. 15. Deberes de la entidad contratante respecto a...",
    }
    loc3 = NormativeSearchEngine.resolve_location(chunk_content)
    assert loc3 == "Art. 15"

    # 4. Fallback a ID estable cuando no hay rotulo especifico
    chunk_fallback = {
        "id": "SEC-999",
        "topic": "Definiciones generales",
        "content": "Para los efectos de la presente normativa...",
    }
    loc4 = NormativeSearchEngine.resolve_location(chunk_fallback)
    assert loc4 == "Fragmento ID SEC-999"


def test_hu21_ca2_inactive_sources_excluded_from_active_search():
    """CA-HU2.1-02: Fuentes inactivas/sustituidas no aparecen en busqueda vigente, pero se preservan en datos."""
    seed_docs = _load_fallback_seed_documents()
    assert len(seed_docs) > 0

    # Verificar que la norma inactiva LEY26850-HIST existe en el repositorio historico
    hist_doc = next((d for d in seed_docs if d["id"] == "LEY26850-HIST"), None)
    assert hist_doc is not None, "El registro historico debe preservarse en el repositorio de datos"
    assert hist_doc["in_force"] is False, "La norma derogada debe figurar con in_force=False"
    assert "Sustituida" in hist_doc["document_name"]

    # Simular busqueda con only_in_force=True para terminos de contrataciones
    query = "contrataciones y adquisiciones del estado adquisicion de bienes"
    kw = NormativeSearchEngine.extract_keywords(query)

    # Filtrar solo vigentes
    active_docs = [d for d in seed_docs if d["in_force"]]
    assert hist_doc not in active_docs, "La norma inactiva no debe estar en la lista de vigentes"

    # Puntuacion sobre documentos vigentes
    active_results = []
    for item in active_docs:
        score = NormativeSearchEngine.score_chunk(item, query, kw)
        if score > 0:
            active_results.append(item)

    # Comprobar que NINGUN resultado pertenece a la norma inactiva
    returned_ids = [r["id"] for r in active_results]
    assert "LEY26850-HIST" not in returned_ids


def test_hu21_ca3_no_evidence_returns_zero_results_without_inventing():
    """CA-HU2.1-03: Sin evidencia -> no genera normas ni articulos ficticios, devuelve lista vacia."""
    seed_docs = _load_fallback_seed_documents()
    active_docs = [d for d in seed_docs if d["in_force"]]

    # Consulta completamente ajena al corpus municipal
    irrelevant_query = "exploracion espacial de satelites en marte y propulsion ionica"
    kw = NormativeSearchEngine.extract_keywords(irrelevant_query)

    results = []
    for item in active_docs:
        score = NormativeSearchEngine.score_chunk(item, irrelevant_query, kw)
        if score > 0:
            results.append(item)

    assert len(results) == 0, "No debe retornar fragmentos inventados para consultas sin sustento"
