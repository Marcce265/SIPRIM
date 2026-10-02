from backend.application.services.pmv1_services import NormativeSearchEngine


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
