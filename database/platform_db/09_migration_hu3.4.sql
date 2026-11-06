-- =========================================================
-- PMV 2 - Sprint 2 - HU3.4: Reanudación de Evaluación desde Checkpoint HITL
-- Idempotente para bases de datos nuevas o existentes.
-- Estrictamente DDL (sin datos semilla de demostración).
-- =========================================================

ALTER TABLE evaluation_checkpoints
    ADD COLUMN IF NOT EXISTS resolved_by_user_id UUID,
    ADD COLUMN IF NOT EXISTS resolution_motive TEXT,
    ADD COLUMN IF NOT EXISTS resolution_conditions TEXT,
    ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(128);

CREATE INDEX IF NOT EXISTS idx_checkpoints_resolved ON evaluation_checkpoints(project_version_id, status);
CREATE INDEX IF NOT EXISTS idx_checkpoints_idempotency ON evaluation_checkpoints(idempotency_key) WHERE idempotency_key IS NOT NULL;
