# backend/tests/test_legal_assessment_service.py
from datetime import datetime
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg.errors import CheckViolation
from psycopg.types.json import Jsonb

from backend.application.services.pmv1_services import (
    LegalAssessmentEngine,
    PlatformService,
)
from backend.domain.exceptions.pmv1_exceptions import (
    ConfiguracionPMV1Error,
    RecursoPMV1NoEncontradoError,
)
from backend.infrastructure.config.settings import get_settings

PROJECT_A_ID = UUID("a0000000-0000-4000-a000-00000000000a")
PROJECT_B_ID = UUID("a0000000-0000-4000-a000-00000000000b")
PROJECT_C_ID = UUID("a0000000-0000-4000-a000-00000000000c")
PROJECT_D_ID = UUID("a0000000-0000-4000-a000-00000000000d")

LEGAL_ADVISOR_ID = UUID("10000000-0000-4000-a000-000000000004")
PLANNER_ID = UUID("10000000-0000-4000-a000-000000000002")


def test_legal_engine_exact_verifiable_citation():
    """
    CA-HU2.2-01: Cuando el sustento identifica un artículo o sección precisa,
    el informe jurídico muestra denominación de la norma, versión, artículo o sección
    y fragmento correspondiente para cotejarlo.
    """
    chunk_id = "LEY-32069-ART53"
    chunks_by_id = {
        chunk_id: {
            "id": chunk_id,
            "document_name": "Ley General de Contrataciones Públicas (Ley 32069)",
            "short_code": "LEY-32069",
            "version": "1.0",
            "chunk_location": "Arts. 53 y 54",
            "content": "Artículo 53.- De las actuaciones preparatorias y expedientes técnicos para obras municipales...",
            "in_force": True,
            "data_origin": "public",
        }
    }

    finding_rows = [
        {
            "id": uuid4(),
            "finding_key": "contratacion_publica",
            "title": "Modalidad de ejecución y topes de contratación pública",
            "description": "Se evaluó la adecuación a la Ley de Contrataciones.",
            "normative_chunk_id": chunk_id,
            "has_precise_reference": True,
            "custom_article_or_section": "Arts. 53 y 54",
            "complies": True,
            "requires_human_review": False,
            "notes": "Alineado a compras públicas vigentes.",
        }
    ]

    result = LegalAssessmentEngine.evaluate(
        project_id=PROJECT_A_ID,
        project_code="PRY-A",
        project_version_id=uuid4(),
        finding_rows=finding_rows,
        chunks_by_id=chunks_by_id,
    )

    assert result["status"] == "verified"
    assert result["verifiable_citations_count"] == 1
    assert result["unverifiable_citations_count"] == 0
    assert result["requires_human_review"] is False

    findings = result["findings"]
    assert len(findings) == 1
    f = findings[0]
    assert f["finding_key"] == "contratacion_publica"
    assert f["complies"] is True
    assert f["requires_human_review"] is False

    citation = f["citation"]
    assert citation["citation_status"] == "verificable"
    assert citation["is_verifiable"] is True
    assert citation["document_name"] == "Ley General de Contrataciones Públicas (Ley 32069)"
    assert citation["version"] == "1.0"
    assert citation["article_or_section"] == "Arts. 53 y 54"
    assert "Artículo 53" in citation["fragment_content"]
    assert citation["citation_hash"] is not None
    assert len(citation["citation_hash"]) == 64  # SHA-256
    assert citation["limitation_note"] is None
    assert citation["is_simulated"] is False
    assert citation["data_origin"] == "public"



def test_legal_engine_simulated_source_is_unverifiable():
    """
    HU2.2: Si la fuente proviene de datos simulados o corpus no oficial,
    la cita NO debe marcarse como verificable ni exponerse como sustento comprobado,
    forzando requires_human_review=True.
    """
    chunk_id = "SIM-CHUNK-1"
    chunks_by_id = {
        chunk_id: {
            "id": chunk_id,
            "document_name": "Reglamento Local Simulado de Prueba",
            "short_code": "SIM-REG",
            "version": "1.0",
            "topic": "Norma simulada (Art. 10)",
            "content": "Art. 10.- Disposición simulada para pruebas...",
            "in_force": True,
            "data_origin": "simulated",
        }
    }

    finding_rows = [
        {
            "id": uuid4(),
            "finding_key": "fuente_simulada_chk",
            "title": "Evaluación con norma simulada",
            "description": "El administrado presentó un reglamento no oficial.",
            "normative_chunk_id": chunk_id,
            "has_precise_reference": True,
            "custom_article_or_section": "Art. 10",
            "complies": True,
            "requires_human_review": False,
        }
    ]

    result = LegalAssessmentEngine.evaluate(
        project_id=PROJECT_B_ID,
        project_code="PRY-B",
        project_version_id=uuid4(),
        finding_rows=finding_rows,
        chunks_by_id=chunks_by_id,
    )

    assert result["status"] == "requires_review"
    assert result["verifiable_citations_count"] == 0
    assert result["unverifiable_citations_count"] == 1
    assert result["requires_human_review"] is True

    f = result["findings"][0]
    assert f["citation"]["citation_status"] == "no_verificable"
    assert f["citation"]["is_verifiable"] is False
    assert f["citation"]["article_or_section"] is None
    assert "simulado" in f["citation"]["limitation_note"].lower()
    assert f["complies"] is None  # Jamás confirmado


def test_legal_engine_apocryphal_article_rejected():
    """
    HU2.2: Si se cita un número de artículo inventado o apócrifo que no coincide
    con el texto del fragmento normativo oficial (ej. 'Art. 9999'), se rechaza la cita
    como no verificable sin fabricar el artículo y requiriendo revisión humana.
    """
    chunk_id = "LEY-32069-TEST"
    chunks_by_id = {
        chunk_id: {
            "id": chunk_id,
            "document_name": "Ley General de Contrataciones Públicas (Ley 32069)",
            "short_code": "LEY-32069",
            "version": "1.0",
            "topic": "Métodos de contratación (Arts. 53 y 54)",
            "content": "Art. 54.1.- Son procedimientos de selección competitivos: a) Licitación pública...",
            "in_force": True,
            "data_origin": "public",
        }
    }

    finding_rows = [
        {
            "id": uuid4(),
            "finding_key": "articulo_apocrifo_chk",
            "title": "Cita apócrifa inexistente",
            "description": "Se alega el Artículo 9999 que no existe en la Ley.",
            "normative_chunk_id": chunk_id,
            "has_precise_reference": True,
            "custom_article_or_section": "Art. 9999",  # Apócrifo
            "complies": True,
            "requires_human_review": False,
        }
    ]

    result = LegalAssessmentEngine.evaluate(
        project_id=PROJECT_B_ID,
        project_code="PRY-B",
        project_version_id=uuid4(),
        finding_rows=finding_rows,
        chunks_by_id=chunks_by_id,
    )

    assert result["status"] == "requires_review"
    assert result["verifiable_citations_count"] == 0
    assert result["unverifiable_citations_count"] == 1
    assert result["requires_human_review"] is True

    f = result["findings"][0]
    assert f["citation"]["citation_status"] == "no_verificable"
    assert f["citation"]["is_verifiable"] is False
    assert f["citation"]["article_or_section"] is None
    assert "no coincide" in f["citation"]["limitation_note"].lower()


def test_legal_engine_fragment_without_article_rejected():
    """
    HU2.2: Si el fragmento normativo no contiene un artículo identificable
    (resumen o preámbulo sin articulado), se rechaza como cita no verificable.
    """
    chunk_id = "PREAMBULO-1"
    chunks_by_id = {
        chunk_id: {
            "id": chunk_id,
            "document_name": "Disposiciones Generales del Plan",
            "short_code": "DISP-GEN",
            "version": "1.0",
            "topic": "Consideraciones preliminares",
            "content": "El presente documento establece las orientaciones y principios generales de la gestión territorial sin articulado específico.",
            "in_force": True,
            "data_origin": "public",
        }
    }

    finding_rows = [
        {
            "id": uuid4(),
            "finding_key": "sin_articulado_chk",
            "title": "Fragmento sin número de artículo",
            "description": "Cita sin artículo verificable.",
            "normative_chunk_id": chunk_id,
            "has_precise_reference": True,
            "custom_article_or_section": None,
            "complies": True,
            "requires_human_review": False,
        }
    ]

    result = LegalAssessmentEngine.evaluate(
        project_id=PROJECT_B_ID,
        project_code="PRY-B",
        project_version_id=uuid4(),
        finding_rows=finding_rows,
        chunks_by_id=chunks_by_id,
    )

    assert result["status"] == "requires_review"
    assert result["verifiable_citations_count"] == 0
    assert result["unverifiable_citations_count"] == 1
    assert result["requires_human_review"] is True

    f = result["findings"][0]
    assert f["citation"]["citation_status"] == "no_verificable"
    assert f["citation"]["article_or_section"] is None


def test_legal_engine_non_compliant_finding_requires_human_review():
    """
    HU2.2 / HU2.3: Si un hallazgo tiene complies=False (ej. incompatibilidad territorial / faja marginal),
    la evaluación completa NO puede declararse como 'cumple'; debe reflejar requires_human_review=True.
    """
    chunk_id = "PDUPDM-04"
    chunks_by_id = {
        chunk_id: {
            "id": chunk_id,
            "document_name": "PDM Huancayo 2017-2037 (O.M. Nº 636-2020-MPH/CM)",
            "short_code": "PDU_EL_TAMBO",
            "version": "2020-OM636",
            "topic": "Zonas de riesgo alto o no mitigable (SINAGERD - Ley 29664)",
            "content": "PDM Huancayo 2017-2037: Las zonas no mitigables son intangibles e inhabitables; se prohíbe la emisión de licencias...",
            "in_force": True,
            "data_origin": "public",
        }
    }

    finding_rows = [
        {
            "id": uuid4(),
            "finding_key": "zonas_riesgo_intangibles",
            "title": "Zonas de riesgo no mitigable y faja marginal (SINAGERD)",
            "description": "El trazo del proyecto invade faja marginal intangible no mitigable.",
            "normative_chunk_id": chunk_id,
            "has_precise_reference": True,
            "custom_article_or_section": "SINAGERD - Ley 29664",
            "complies": False,  # NO CUMPLE
            "requires_human_review": True,
        }
    ]

    result = LegalAssessmentEngine.evaluate(
        project_id=PROJECT_D_ID,
        project_code="PRY-D",
        project_version_id=uuid4(),
        finding_rows=finding_rows,
        chunks_by_id=chunks_by_id,
    )

    assert result["status"] == "requires_review"
    assert result["requires_human_review"] is True
    assert result["verifiable_citations_count"] == 1
    assert result["unverifiable_citations_count"] == 0

    f = result["findings"][0]
    assert f["complies"] is False
    assert f["requires_human_review"] is True


def test_legal_engine_human_review_finding_propagates_even_with_verified_citations():
    """
    HU2.2: Si todos los hallazgos tienen citas verificables pero uno tiene requires_human_review=True,
    la evaluación general debe tener requires_human_review=True y status='requires_review'.
    """
    chunk_id = "LEY-32069-VALID"
    chunks_by_id = {
        chunk_id: {
            "id": chunk_id,
            "document_name": "Ley General de Contrataciones Públicas",
            "short_code": "LEY-32069",
            "version": "1.0",
            "topic": "Actuaciones preparatorias (Art. 46)",
            "content": "Art. 46.1.- El requerimiento da inicio al proceso de contratación...",
            "in_force": True,
            "data_origin": "public",
        }
    }

    finding_rows = [
        {
            "id": uuid4(),
            "finding_key": "req_revision_manual",
            "title": "Revisión especial de convenio",
            "description": "Cita exacta verificable, pero requiere verificación manual del convenio de coejecución.",
            "normative_chunk_id": chunk_id,
            "has_precise_reference": True,
            "custom_article_or_section": "Art. 46",
            "complies": True,
            "requires_human_review": True,  # Requiere revisión
        }
    ]

    result = LegalAssessmentEngine.evaluate(
        project_id=PROJECT_A_ID,
        project_code="PRY-A",
        project_version_id=uuid4(),
        finding_rows=finding_rows,
        chunks_by_id=chunks_by_id,
    )

    assert result["status"] == "requires_review"
    assert result["requires_human_review"] is True
    assert result["verifiable_citations_count"] == 1

def test_legal_engine_unverifiable_citation_no_fabricated_article():
    """
    CA-HU2.2-02: Cuando no se puede ubicar una referencia precisa, el informe indica
    'Cita no verificable', marca el hallazgo para revisión humana y no inventa un número de artículo.
    """
    finding_rows = [
        {
            "id": uuid4(),
            "finding_key": "urbanismo_desarrollo",
            "title": "Alineamiento y fajas de servidumbre en área de expansión",
            "description": "Se detecta solicitud sin sustento de plano ni artículo de zonificación.",
            "normative_chunk_id": None,  # No se pudo ubicar referencia precisa
            "has_precise_reference": False,
            "custom_article_or_section": None,
            "complies": None,  # Nunca confirmado
            "requires_human_review": True,
            "notes": "El administrado cita genéricamente el PDM Huancayo sin indicar artículo.",
        }
    ]

    result = LegalAssessmentEngine.evaluate(
        project_id=PROJECT_B_ID,
        project_code="PRY-B",
        project_version_id=uuid4(),
        finding_rows=finding_rows,
        chunks_by_id={},
    )

    assert result["status"] == "requires_review"
    assert result["verifiable_citations_count"] == 0
    assert result["unverifiable_citations_count"] == 1
    assert result["requires_human_review"] is True

    findings = result["findings"]
    assert len(findings) == 1
    f = findings[0]
    # No inventa artículo
    assert f["citation"]["article_or_section"] is None
    assert f["citation"]["citation_status"] == "no_verificable"
    assert f["citation"]["is_verifiable"] is False
    assert f["citation"]["status_label"] == "Cita no verificable"
    assert f["citation"]["limitation_note"] is not None
    assert "no identifica un artículo o sección precisa" in f["citation"]["limitation_note"]
    assert f["requires_human_review"] is True
    assert f["complies"] is None  # NUNCA favorable ni confirmado


def test_legal_engine_derogated_or_substituted_norm_is_unverifiable():
    """
    Una norma derogada o no vigente (in_force = False) no debe generar una cita verificable
    favorable, sino marcarse como Cita no verificable y requerir revisión humana.
    """
    chunk_id = "LEY26850-HIST-1"
    chunks_by_id = {
        chunk_id: {
            "id": chunk_id,
            "document_name": "Ley de Contrataciones y Adquisiciones del Estado (Ley 26850) [Derogada]",
            "short_code": "LEY-26850",
            "version": "1.0",
            "chunk_location": "Art. 12",
            "content": "Texto histórico de ley derogada...",
            "in_force": False,  # NO VIGENTE
            "data_origin": "simulated",
        }
    }

    finding_rows = [
        {
            "id": uuid4(),
            "finding_key": "contrataciones_historico",
            "title": "Aplicación de Ley derogada",
            "description": "El expediente cita la antigua Ley 26850 sustituida.",
            "normative_chunk_id": chunk_id,
            "has_precise_reference": True,
            "custom_article_or_section": "Art. 12",
            "complies": None,
            "requires_human_review": True,
            "notes": "Norma derogada",
        }
    ]

    result = LegalAssessmentEngine.evaluate(
        project_id=PROJECT_B_ID,
        project_code="PRY-B",
        project_version_id=uuid4(),
        finding_rows=finding_rows,
        chunks_by_id=chunks_by_id,
    )

    assert result["verifiable_citations_count"] == 0
    assert result["unverifiable_citations_count"] == 1
    assert result["requires_human_review"] is True

    f = result["findings"][0]
    assert f["citation"]["citation_status"] == "no_verificable"
    assert f["citation"]["is_verifiable"] is False
    assert "derogada o sustituida" in f["citation"]["limitation_note"]


def test_legal_engine_unverifiable_forces_complies_to_none():
    """
    Si una regla intenta establecer complies=True pero has_precise_reference=False,
    el motor anula complies a None y fuerza requires_human_review=True.
    """
    finding_rows = [
        {
            "id": uuid4(),
            "finding_key": "competencias_irregulares",
            "title": "Sin referencia precisa",
            "description": "Intento de dar conformidad sin cita verificable.",
            "normative_chunk_id": None,
            "has_precise_reference": False,
            "custom_article_or_section": None,
            "complies": True,  # Intento indebido
            "requires_human_review": False,
            "notes": "Nota",
        }
    ]

    result = LegalAssessmentEngine.evaluate(
        project_id=PROJECT_B_ID,
        project_code="PRY-B",
        project_version_id=uuid4(),
        finding_rows=finding_rows,
        chunks_by_id={},
    )

    f = result["findings"][0]
    assert f["complies"] is None
    assert f["requires_human_review"] is True
    assert f["citation"]["citation_status"] == "no_verificable"
    assert f["citation"]["article_or_section"] is None


def test_db_check_constraints_legal_findings():
    """
    Comprueba las restricciones check de integridad a nivel de base de datos para HU2.2:
    1. chk_legal_finding_unverifiable: Si has_precise_reference=FALSE, complies NO puede ser TRUE.
    2. chk_legal_finding_no_fabricated_article: Si has_precise_reference=FALSE, custom_article_or_section debe ser NULL.
    """
    settings = get_settings()
    db_url = settings.platform_db_url.replace("postgresql+psycopg://", "postgresql://", 1)

    with psycopg.connect(db_url) as conn:
        # 1. Intento de complies=TRUE sin referencia precisa -> CheckViolation
        with pytest.raises(CheckViolation):
            with conn.transaction():
                conn.execute(
                    """
                    INSERT INTO project_legal_findings
                    (id, project_id, project_code, finding_key, title, description,
                     has_precise_reference, complies)
                    VALUES (%s, %s, 'PRY-B', 'urbanismo_chk', 'Intento Invalido', 'Test',
                            FALSE, TRUE)
                    """,
                    (uuid4(), PROJECT_B_ID),
                )

        # 2. Intento de inventar un artículo cuando no hay referencia precisa -> CheckViolation
        with pytest.raises(CheckViolation):
            with conn.transaction():
                conn.execute(
                    """
                    INSERT INTO project_legal_findings
                    (id, project_id, project_code, finding_key, title, description,
                     has_precise_reference, custom_article_or_section, complies)
                    VALUES (%s, %s, 'PRY-B', 'urbanismo_chk', 'Intento Articulo Inventado', 'Test',
                            FALSE, 'Art. 99 Inventado', NULL)
                    """,
                    (uuid4(), PROJECT_B_ID),
                )


def test_platform_service_legal_assessment_persistence_and_traceability():
    """
    Prueba de integración en la base de datos real:
    - Ejecuta evaluate_legal_assessment para PRY-A (con citas exactas).
    - Persiste en legal_assessments y project_legal_findings.
    - get_legal_assessment recupera la evaluación con sus citas y hashes intactos.
    - Ejecuta evaluate_legal_assessment para PRY-B (con citas no verificables).
    - Confirma que PRY-B tiene 'Cita no verificable', sin artículos inventados y requiere revisión humana.
    """
    settings = get_settings()
    service = PlatformService(
        db_url=settings.platform_db_url,
        dispatcher=None,  # type: ignore
        enable_demo_fallback=False,
    )

    # 1. PRY-A: evaluación con citas exactas
    eval_a = service.evaluate_legal_assessment(PROJECT_A_ID, LEGAL_ADVISOR_ID)
    assert str(eval_a["project_id"]) == str(PROJECT_A_ID)
    assert eval_a["status"] == "verified"
    assert eval_a["verifiable_citations_count"] >= 3
    assert eval_a["unverifiable_citations_count"] == 0
    assert eval_a["requires_human_review"] is False

    # Verificar que cada hallazgo tiene su cita verificable
    for f in eval_a["findings"]:
        cit = f["citation"]
        assert cit["citation_status"] == "verificable"
        assert cit["is_verifiable"] is True
        assert cit["document_name"] is not None
        assert cit["version"] is not None
        assert cit["article_or_section"] is not None
        assert cit["fragment_content"] is not None
        assert cit["citation_hash"] is not None
        assert cit["limitation_note"] is None

    # 2. Recuperación persistida de PRY-A
    get_a = service.get_legal_assessment(PROJECT_A_ID)
    assert get_a["assessment_id"] == eval_a["assessment_id"]
    assert get_a["verifiable_citations_count"] == eval_a["verifiable_citations_count"]
    assert len(get_a["findings"]) == len(eval_a["findings"])
    assert get_a["findings"][0]["citation"]["citation_hash"] == eval_a["findings"][0]["citation"]["citation_hash"]

    # 3. PRY-B: evaluación con citas no verificables
    eval_b = service.evaluate_legal_assessment(PROJECT_B_ID, LEGAL_ADVISOR_ID)
    assert str(eval_b["project_id"]) == str(PROJECT_B_ID)
    assert eval_b["status"] == "requires_review"
    assert eval_b["unverifiable_citations_count"] >= 2
    assert eval_b["requires_human_review"] is True

    # Verificar hallazgos no verificables de PRY-B
    unverifiable_found = False
    for f in eval_b["findings"]:
        cit = f["citation"]
        if not cit["is_verifiable"]:
            unverifiable_found = True
            assert cit["citation_status"] == "no_verificable"
            assert cit["article_or_section"] is None  # No inventa artículo
            assert cit["status_label"] == "Cita no verificable"
            assert f["requires_human_review"] is True
            assert cit["limitation_note"] is not None

    assert unverifiable_found is True

    # 4. Recuperación persistida de PRY-B
    get_b = service.get_legal_assessment(PROJECT_B_ID)
    assert get_b["status"] == "requires_review"
    assert get_b["requires_human_review"] is True
