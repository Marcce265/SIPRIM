-- =========================================================
-- PMV 2 - Sprint 2 - HU2.3: Generar alerta legal e impedir aprobación/priorización
-- Idempotente para bases de datos nuevas o existentes.
-- =========================================================

-- 1. Modificar restricción de status en legal_assessments para admitir 'alerta_legal'
ALTER TABLE legal_assessments DROP CONSTRAINT IF EXISTS legal_assessments_status_check;
ALTER TABLE legal_assessments ADD CONSTRAINT legal_assessments_status_check
    CHECK (status IN ('requires_review', 'verified', 'insufficient', 'alerta_legal'));

-- 2. Añadir columnas de control de alerta legal en legal_assessments
ALTER TABLE legal_assessments ADD COLUMN IF NOT EXISTS has_legal_alert BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE legal_assessments ADD COLUMN IF NOT EXISTS legal_alert_motive TEXT;
ALTER TABLE legal_assessments ADD COLUMN IF NOT EXISTS legal_alert_norm VARCHAR(255);
ALTER TABLE legal_assessments ADD COLUMN IF NOT EXISTS is_resolved BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE legal_assessments ADD COLUMN IF NOT EXISTS resolved_by_user_id UUID;
ALTER TABLE legal_assessments ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ;
ALTER TABLE legal_assessments ADD COLUMN IF NOT EXISTS resolution_justification TEXT;

-- 3. Vincular hallazgos legales con la versión específica del expediente para aislamiento estricto
ALTER TABLE project_legal_findings ADD COLUMN IF NOT EXISTS project_version_id UUID REFERENCES project_versions(id) ON DELETE CASCADE;

-- Backfill project_version_id para registros iniciales
UPDATE project_legal_findings plf
SET project_version_id = (
    SELECT pv.id FROM project_versions pv
    WHERE pv.project_id = plf.project_id
    ORDER BY pv.version_number ASC LIMIT 1
)
WHERE plf.project_version_id IS NULL;

-- 4. Tabla de resoluciones y levantamientos de alertas legales por Asesoría Jurídica
CREATE TABLE IF NOT EXISTS legal_alert_resolutions (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    project_version_id UUID NOT NULL REFERENCES project_versions(id) ON DELETE CASCADE,
    resolved_by_user_id UUID NOT NULL,
    resolution_action VARCHAR(64) NOT NULL,
    justification TEXT NOT NULL,
    resolved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    idempotency_key VARCHAR(120) NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS legal_alert_resolutions_proj_idx ON legal_alert_resolutions(project_id, project_version_id);
