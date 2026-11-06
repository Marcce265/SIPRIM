-- =========================================================
-- PMV 2 - Sprint 2 - HU1.9: Estimación de duración de obra e incertidumbre (PERT)
-- Registro de duraciones optimista (a), más probable (m), pesimista (b)
-- y cálculo de duración esperada, desviación estándar y varianza vinculados
-- al proyecto y a su versión exacta.
-- Idempotente para bases de datos nuevas o existentes.
-- Estrictamente DDL (sin datos semilla de demostración).
-- =========================================================

CREATE TABLE IF NOT EXISTS project_pert_estimates (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    project_version_id UUID NOT NULL REFERENCES project_versions(id) ON DELETE CASCADE,
    registered_by_user_id UUID NOT NULL,
    time_unit VARCHAR(20) NOT NULL DEFAULT 'meses'
        CHECK (time_unit IN ('meses', 'días', 'semanas')),
    optimistic_duration NUMERIC(10, 4) NOT NULL,
    most_likely_duration NUMERIC(10, 4) NOT NULL,
    pessimistic_duration NUMERIC(10, 4) NOT NULL,
    expected_duration NUMERIC(10, 4) NOT NULL,
    standard_deviation NUMERIC(10, 4) NOT NULL,
    variance NUMERIC(10, 4) NOT NULL,
    confidence_interval_low NUMERIC(10, 4) NOT NULL,
    confidence_interval_high NUMERIC(10, 4) NOT NULL,
    formula_applied TEXT NOT NULL,
    disclaimer TEXT NOT NULL,
    explanation TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_pert_project_version UNIQUE (project_version_id),
    CONSTRAINT chk_pert_order CHECK (
        optimistic_duration >= 0 AND
        most_likely_duration >= optimistic_duration AND
        pessimistic_duration >= most_likely_duration
    )
);

CREATE INDEX IF NOT EXISTS idx_pert_project ON project_pert_estimates(project_id);
CREATE INDEX IF NOT EXISTS idx_pert_version ON project_pert_estimates(project_version_id);
