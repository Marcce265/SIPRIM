-- =========================================================
-- PMV 2 - Sprint 2 - HU3.1: Migración DDL Pausa ante Riesgos Altos y Checkpoints Persistentes
-- Idempotente para bases de datos nuevas o existentes.
-- Estrictamente DDL (sin datos semilla de demostración).
-- =========================================================

-- 1. Ampliar estados válidos en tabla projects para incluir 'pending_review'
ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_status_check;
ALTER TABLE projects ADD CONSTRAINT projects_status_check
    CHECK (status IN ('draft', 'ready', 'evaluating', 'evaluated', 'approved', 'rejected', 'observed', 'error', 'pending_review'));

-- 2. Ampliar estados válidos en tabla evaluations para incluir 'pending_review'
ALTER TABLE evaluations DROP CONSTRAINT IF EXISTS evaluations_status_check;
ALTER TABLE evaluations ADD CONSTRAINT evaluations_status_check
    CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'pending_review'));

-- 3. Tabla de puntos de control persistentes (Checkpoints HITL)
CREATE TABLE IF NOT EXISTS evaluation_checkpoints (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    project_version_id UUID NOT NULL REFERENCES project_versions(id) ON DELETE CASCADE,
    evaluation_id UUID REFERENCES evaluations(id) ON DELETE SET NULL,
    checkpoint_type VARCHAR(40) NOT NULL DEFAULT 'high_risk_pause',
    status VARCHAR(32) NOT NULL DEFAULT 'pending_review'
        CHECK (status IN ('pending_review', 'resolved', 'dismissed')),
    reason TEXT NOT NULL,
    risk_source VARCHAR(60) NOT NULL,
    risk_level VARCHAR(32) NOT NULL DEFAULT 'high',
    details JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_checkpoint_version_source UNIQUE (project_version_id, risk_source, checkpoint_type)
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_project ON evaluation_checkpoints(project_id, status);
CREATE INDEX IF NOT EXISTS idx_checkpoints_version ON evaluation_checkpoints(project_version_id, status);

-- 4. Soporte de aislamiento real por versión en evidencias ambientales y áreas verdes
ALTER TABLE project_environmental_records
    ADD COLUMN IF NOT EXISTS project_version_id UUID REFERENCES project_versions(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_project_env_version ON project_environmental_records(project_version_id);

ALTER TABLE project_green_area_records
    ADD COLUMN IF NOT EXISTS project_version_id UUID REFERENCES project_versions(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_project_green_version ON project_green_area_records(project_version_id);

-- 5. Backfill de project_version_id para registros preexistentes hacia la versión 1 de cada proyecto
UPDATE project_environmental_records r
SET project_version_id = (
    SELECT pv.id FROM project_versions pv
    WHERE pv.project_id = r.project_id AND pv.version_number = 1
    LIMIT 1
)
WHERE r.project_version_id IS NULL;

UPDATE project_green_area_records r
SET project_version_id = (
    SELECT pv.id FROM project_versions pv
    WHERE pv.project_id = r.project_id AND pv.version_number = 1
    LIMIT 1
)
WHERE r.project_version_id IS NULL;
