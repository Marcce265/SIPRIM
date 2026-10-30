-- =========================================================
-- PMV 2 - Sprint 2 - HU2.2: Migración DDL Citar Artículo Exacto de la Normativa
-- Idempotente para bases de datos nuevas o existentes.
-- Estrictamente DDL (sin datos semilla de demostración).
-- =========================================================

CREATE TABLE IF NOT EXISTS project_legal_findings (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    project_code VARCHAR(40) NOT NULL,
    finding_key VARCHAR(60) NOT NULL,
    title VARCHAR(180) NOT NULL,
    description TEXT NOT NULL,
    normative_chunk_id VARCHAR(40) REFERENCES normative_documents(id) ON DELETE SET NULL,
    has_precise_reference BOOLEAN NOT NULL DEFAULT TRUE,
    custom_article_or_section VARCHAR(80),
    complies BOOLEAN,
    requires_human_review BOOLEAN NOT NULL DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_legal_finding_unverifiable CHECK (
        (has_precise_reference = FALSE AND (complies IS NULL OR complies = FALSE)) OR
        (has_precise_reference = TRUE)
    ),
    CONSTRAINT chk_legal_finding_no_fabricated_article CHECK (
        (has_precise_reference = TRUE AND custom_article_or_section IS NOT NULL AND length(trim(custom_article_or_section)) > 0) OR
        (has_precise_reference = FALSE AND custom_article_or_section IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS legal_findings_proj_idx ON project_legal_findings(project_id, finding_key);
CREATE INDEX IF NOT EXISTS legal_findings_code_idx ON project_legal_findings(project_code, finding_key);

CREATE TABLE IF NOT EXISTS legal_assessments (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    project_code VARCHAR(40) NOT NULL,
    project_version_id UUID REFERENCES project_versions(id) ON DELETE SET NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'requires_review'
        CHECK (status IN ('requires_review', 'verified', 'insufficient')),
    summary TEXT NOT NULL,
    findings_json JSONB NOT NULL,
    total_findings INTEGER NOT NULL DEFAULT 0,
    verifiable_citations_count INTEGER NOT NULL DEFAULT 0,
    unverifiable_citations_count INTEGER NOT NULL DEFAULT 0,
    requires_human_review BOOLEAN NOT NULL DEFAULT TRUE,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_legal_assessment_project UNIQUE (project_id)
);

CREATE INDEX IF NOT EXISTS legal_assessment_proj_idx ON legal_assessments(project_id);
CREATE INDEX IF NOT EXISTS legal_assessment_code_idx ON legal_assessments(project_code);
