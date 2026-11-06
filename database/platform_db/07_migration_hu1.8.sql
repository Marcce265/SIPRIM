-- =========================================================
-- PMV 2 - Sprint 2 - HU1.8: Migración DDL de Viabilidad Técnica del Proyecto
-- Evaluación técnica preliminar de parámetros y criterios de ingeniería (RNE / Invierte.pe).
-- Idempotente para bases de datos nuevas o existentes.
-- Estrictamente DDL (sin datos semilla de demostración).
-- =========================================================

CREATE TABLE IF NOT EXISTS project_technical_parameters (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    project_version_id UUID NOT NULL REFERENCES project_versions(id) ON DELETE CASCADE,
    criterion_code VARCHAR(40) NOT NULL,
    criterion_name VARCHAR(200) NOT NULL,
    normative_reference VARCHAR(240) NOT NULL,
    normative_version VARCHAR(40) NOT NULL DEFAULT 'vigente',
    has_sufficient_data BOOLEAN NOT NULL DEFAULT TRUE,
    parameter_name VARCHAR(120),
    parameter_value_numeric NUMERIC(10, 2),
    parameter_unit VARCHAR(32),
    parameter_value_text VARCHAR(240),
    applied_rule TEXT NOT NULL,
    supporting_document VARCHAR(300),
    source_origin VARCHAR(16) NOT NULL DEFAULT 'declared'
        CHECK (source_origin IN ('declared', 'simulated', 'public')),
    is_simulated BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_tech_param_version_criterion UNIQUE (project_version_id, criterion_code),
    CONSTRAINT chk_tech_param_sufficiency CHECK (
        (has_sufficient_data = TRUE AND (parameter_value_numeric IS NOT NULL OR parameter_value_text IS NOT NULL) AND supporting_document IS NOT NULL) OR
        (has_sufficient_data = FALSE)
    )
);

CREATE INDEX IF NOT EXISTS idx_tech_param_proj_ver ON project_technical_parameters(project_id, project_version_id);
CREATE INDEX IF NOT EXISTS idx_tech_param_code ON project_technical_parameters(criterion_code);

CREATE TABLE IF NOT EXISTS technical_feasibility_assessments (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    project_version_id UUID NOT NULL REFERENCES project_versions(id) ON DELETE CASCADE,
    requested_by_user_id UUID NOT NULL,
    idempotency_key VARCHAR(120) NOT NULL UNIQUE,
    status VARCHAR(32) NOT NULL DEFAULT 'completed'
        CHECK (status IN ('completed', 'failed')),
    overall_result VARCHAR(32) NOT NULL
        CHECK (overall_result IN ('cumple', 'observado', 'informacion_insuficiente', 'pendiente_revision')),
    overall_result_label VARCHAR(80) NOT NULL,
    is_viable BOOLEAN NOT NULL DEFAULT FALSE,
    is_preliminary_opinion BOOLEAN NOT NULL DEFAULT TRUE,
    disclaimer TEXT NOT NULL,
    summary TEXT NOT NULL,
    criteria_summary JSONB NOT NULL,
    findings_json JSONB NOT NULL,
    technical_score NUMERIC(5, 2),
    score_explanation TEXT,
    dimension_conclusion TEXT NOT NULL,
    dimension_justification TEXT NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_tech_assess_version UNIQUE (project_version_id)
);

CREATE INDEX IF NOT EXISTS idx_tech_assess_proj_ver ON technical_feasibility_assessments(project_id, project_version_id, evaluated_at DESC);
