-- =========================================================
-- PMV 1 · ms-economic · base economic_db
-- Fuente: BASES_DE_DATOS_PMV1_MICROSERVICIOS.md, seccion 8.3
-- Ejecutar SOLO en economic_db. Se puede ejecutar varias veces.
-- evaluation_id, project_version_id y criteria_version_id vienen de ms-platform: SIN FK.
-- =========================================================
CREATE TABLE IF NOT EXISTS economic_assessments (
    id UUID PRIMARY KEY,
    evaluation_id UUID NOT NULL UNIQUE,
    project_version_id UUID NOT NULL,
    criteria_version_id UUID NOT NULL,
    budget_snapshot_pen NUMERIC(18,2) NOT NULL CHECK (budget_snapshot_pen > 0),
    beneficiaries_snapshot INTEGER NOT NULL CHECK (beneficiaries_snapshot > 0),
    excellent_cost_snapshot_pen NUMERIC(18,2) NOT NULL CHECK (excellent_cost_snapshot_pen > 0),
    unacceptable_cost_snapshot_pen NUMERIC(18,2) NOT NULL,
    cost_per_beneficiary_pen NUMERIC(18,2) NOT NULL CHECK (cost_per_beneficiary_pen >= 0),
    score_0_100 NUMERIC(5,2) NOT NULL CHECK (score_0_100 BETWEEN 0 AND 100),
    status VARCHAR(16) NOT NULL DEFAULT 'completed' CHECK (status = 'completed'),
    explanation TEXT NOT NULL,
    algorithm_version VARCHAR(40) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT economic_thresholds_order
        CHECK (unacceptable_cost_snapshot_pen > excellent_cost_snapshot_pen)
);

CREATE TABLE IF NOT EXISTS assessment_metrics (
    id UUID PRIMARY KEY,
    assessment_id UUID NOT NULL REFERENCES economic_assessments(id) ON DELETE RESTRICT,
    metric_code VARCHAR(50) NOT NULL,
    numeric_value NUMERIC(18,4) NOT NULL,
    unit VARCHAR(40) NOT NULL,
    formula TEXT NOT NULL,
    UNIQUE (assessment_id, metric_code)
);

CREATE TABLE IF NOT EXISTS processed_requests (
    event_id UUID PRIMARY KEY,
    evaluation_id UUID NOT NULL UNIQUE,
    assessment_id UUID NOT NULL UNIQUE REFERENCES economic_assessments(id) ON DELETE RESTRICT,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS economic_project_version_idx ON economic_assessments(project_version_id, created_at DESC);
