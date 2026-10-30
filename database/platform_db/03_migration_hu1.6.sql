-- =========================================================
-- PMV 2 - Sprint 2 - HU1.6: Migración de Evaluación de Impacto Ambiental
-- Idempotente para instalaciones nuevas o existentes.
-- Estrictamente DDL (sin datos semilla de demostración).
-- =========================================================

CREATE TABLE IF NOT EXISTS project_environmental_records (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    project_code VARCHAR(40) NOT NULL,
    has_sufficient_data BOOLEAN NOT NULL DEFAULT TRUE,
    environmental_component VARCHAR(64) NOT NULL,
    declared_impacts TEXT,
    declared_measures TEXT,
    verifiable_evidence TEXT,
    proximity_to_water_meters NUMERIC(10,2),
    is_in_protected_or_risk_area BOOLEAN DEFAULT NULL,
    source_name VARCHAR(240) NOT NULL,
    data_origin VARCHAR(16) NOT NULL DEFAULT 'simulated'
        CHECK (data_origin IN ('declared', 'simulated', 'public')),
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_env_insufficient_no_evidence CHECK (
        (has_sufficient_data = TRUE AND verifiable_evidence IS NOT NULL AND is_in_protected_or_risk_area IS NOT NULL) OR
        (has_sufficient_data = FALSE AND verifiable_evidence IS NULL AND is_in_protected_or_risk_area IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS env_records_project_idx ON project_environmental_records(project_id, environmental_component);
CREATE INDEX IF NOT EXISTS env_records_code_idx ON project_environmental_records(project_code);

CREATE TABLE IF NOT EXISTS environmental_assessments (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    project_version_id UUID NOT NULL REFERENCES project_versions(id) ON DELETE RESTRICT,
    assessed_by_user_id UUID NOT NULL,
    idempotency_key VARCHAR(120) NOT NULL UNIQUE,
    status VARCHAR(32) NOT NULL,
    risk_level VARCHAR(32) NOT NULL,
    risk_observation TEXT,
    requires_human_review BOOLEAN NOT NULL DEFAULT FALSE,
    favorable BOOLEAN,
    summary TEXT NOT NULL,
    declared_vs_evidence_json JSONB NOT NULL,
    impacts_json JSONB NOT NULL,
    mitigations_json JSONB NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_insufficient_not_favorable CHECK (
        status <> 'insufficient' OR favorable IS NOT TRUE
    ),
    CONSTRAINT chk_high_risk_requires_human_review CHECK (
        risk_level <> 'high' OR requires_human_review = TRUE
    ),
    CONSTRAINT chk_high_risk_not_auto_favorable CHECK (
        risk_level <> 'high' OR favorable IS NOT TRUE
    )
);

CREATE INDEX IF NOT EXISTS env_assessments_project_idx ON environmental_assessments(project_id, evaluated_at DESC);
CREATE INDEX IF NOT EXISTS env_assessments_risk_idx ON environmental_assessments(risk_level);

-- =========================================================
-- Ajustes idempotentes para bases de datos existentes
-- =========================================================

-- Permite que is_in_protected_or_risk_area sea NULL y no fuerce FALSE
ALTER TABLE project_environmental_records
    ALTER COLUMN is_in_protected_or_risk_area DROP NOT NULL;
ALTER TABLE project_environmental_records
    ALTER COLUMN is_in_protected_or_risk_area SET DEFAULT NULL;

-- Corrige registros existentes donde un dato ausente se interpretó erróneamente como FALSE
UPDATE project_environmental_records
SET is_in_protected_or_risk_area = NULL
WHERE has_sufficient_data = FALSE AND is_in_protected_or_risk_area = FALSE;

-- Actualiza la restricción CHECK para que exija NULL en ausencia de datos suficientes
ALTER TABLE project_environmental_records
    DROP CONSTRAINT IF EXISTS chk_env_insufficient_no_evidence;
ALTER TABLE project_environmental_records
    ADD CONSTRAINT chk_env_insufficient_no_evidence CHECK (
        (has_sufficient_data = TRUE AND verifiable_evidence IS NOT NULL AND is_in_protected_or_risk_area IS NOT NULL) OR
        (has_sufficient_data = FALSE AND verifiable_evidence IS NULL AND is_in_protected_or_risk_area IS NULL)
    );
