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
