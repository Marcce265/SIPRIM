-- =========================================================
-- PMV 2 - Sprint 2 - HU1.5: Migración DDL de Equidad de Género y Edad
-- Idempotente para bases nuevas o existentes.
-- Estrictamente DDL (sin datos semilla de demostración).
-- =========================================================

CREATE TABLE IF NOT EXISTS project_demographic_equity_records (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    project_code VARCHAR(40) NOT NULL,
    dimension VARCHAR(32) NOT NULL CHECK (dimension IN ('genero', 'edad')),
    has_sufficient_data BOOLEAN NOT NULL DEFAULT TRUE,
    target_group VARCHAR(120) NOT NULL,
    aggregated_population INTEGER,
    aggregated_percentage NUMERIC(5,2),
    equity_criterion VARCHAR(240) NOT NULL,
    declared_benefit TEXT,
    verifiable_data TEXT,
    has_favorable_evidence BOOLEAN NOT NULL DEFAULT FALSE,
    score_effect_pts NUMERIC(5,2),
    effect_type VARCHAR(32) NOT NULL DEFAULT 'indeterminado'
        CHECK (effect_type IN ('favorable', 'neutro', 'desfavorable', 'indeterminado')),
    effect_explanation TEXT NOT NULL,
    source_name VARCHAR(240) NOT NULL,
    data_origin VARCHAR(16) NOT NULL DEFAULT 'simulated'
        CHECK (data_origin IN ('declared', 'simulated', 'public')),
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_equity_insufficient CHECK (
        (has_sufficient_data = TRUE AND aggregated_percentage IS NOT NULL AND score_effect_pts IS NOT NULL) OR
        (has_sufficient_data = FALSE AND aggregated_percentage IS NULL AND aggregated_population IS NULL AND score_effect_pts IS NULL AND effect_type = 'indeterminado')
    ),
    CONSTRAINT chk_equity_percentage_range CHECK (
        aggregated_percentage IS NULL OR (aggregated_percentage >= 0.0 AND aggregated_percentage <= 100.0)
    )
);

CREATE INDEX IF NOT EXISTS demographic_equity_proj_idx ON project_demographic_equity_records(project_id, dimension);
CREATE INDEX IF NOT EXISTS demographic_equity_code_idx ON project_demographic_equity_records(project_code, dimension);

-- Columnas de extensión para social_accessibility_assessments (HU1.5)
ALTER TABLE social_accessibility_assessments
    ADD COLUMN IF NOT EXISTS equity_json JSONB,
    ADD COLUMN IF NOT EXISTS social_score NUMERIC(5,2),
    ADD COLUMN IF NOT EXISTS score_explanation TEXT;
