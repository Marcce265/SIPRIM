-- =========================================================
-- PMV 2 - Sprint 2 - HU1.4: Migración DDL de Accesibilidad Social
-- Idempotente para instalaciones nuevas o existentes.
-- Estrictamente DDL (sin datos semilla de demostración).
-- =========================================================

CREATE TABLE IF NOT EXISTS territorial_social_indicators (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    project_code VARCHAR(40) NOT NULL,
    category VARCHAR(32) NOT NULL CHECK (category IN ('salud', 'educacion', 'transporte')),
    indicator_name VARCHAR(240) NOT NULL,
    metric_value NUMERIC(10,2),
    metric_unit VARCHAR(32),
    has_sufficient_data BOOLEAN NOT NULL DEFAULT TRUE,
    source_name VARCHAR(240) NOT NULL,
    data_origin VARCHAR(16) NOT NULL DEFAULT 'simulated'
        CHECK (data_origin IN ('declared', 'simulated', 'public')),
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_insufficient_no_value CHECK (
        (has_sufficient_data = TRUE AND metric_value IS NOT NULL AND metric_unit IS NOT NULL) OR
        (has_sufficient_data = FALSE AND metric_value IS NULL AND metric_unit IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS territorial_social_proj_cat_idx ON territorial_social_indicators(project_id, category);
CREATE INDEX IF NOT EXISTS territorial_social_code_cat_idx ON territorial_social_indicators(project_code, category);

CREATE TABLE IF NOT EXISTS social_accessibility_assessments (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    project_version_id UUID NOT NULL REFERENCES project_versions(id) ON DELETE RESTRICT,
    requested_by_user_id UUID NOT NULL,
    idempotency_key VARCHAR(120) NOT NULL UNIQUE,
    status VARCHAR(32) NOT NULL DEFAULT 'completed',
    summary TEXT NOT NULL,
    results_json JSONB NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS social_assess_proj_idx ON social_accessibility_assessments(project_id, evaluated_at DESC);
