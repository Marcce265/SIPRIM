-- =========================================================
-- PMV 2 - Sprint 2 - HU1.7: Migración DDL de Conservación de Áreas Verdes
-- Idempotente para instalaciones nuevas o volúmenes existentes.
-- Estrictamente DDL (sin datos semilla de demostración).
-- =========================================================

CREATE TABLE IF NOT EXISTS project_green_area_records (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    project_code VARCHAR(40) NOT NULL,
    has_sufficient_data BOOLEAN NOT NULL DEFAULT TRUE,
    total_project_area_m2 NUMERIC(10,2),
    green_area_m2 NUMERIC(10,2),
    green_area_percentage NUMERIC(5,2),
    delimitation_description TEXT,
    declared_affectation TEXT,
    verifiable_affectation TEXT,
    affectation_type VARCHAR(40)
        CHECK (affectation_type IN (
            'conservacion_positiva',
            'afectacion_mitigada',
            'afectacion_no_mitigada',
            'sin_afectacion',
            'indeterminada'
        )),
    protection_measures TEXT,
    has_sufficient_measures BOOLEAN NOT NULL DEFAULT TRUE,
    score_effect_pts NUMERIC(5,2),
    effect_type VARCHAR(32)
        CHECK (effect_type IN ('bonus', 'penalizacion', 'neutro', 'indeterminado')),
    calculation_explanation TEXT,
    source_name VARCHAR(240) NOT NULL,
    data_origin VARCHAR(16) NOT NULL DEFAULT 'simulated'
        CHECK (data_origin IN ('declared', 'simulated', 'public')),
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_green_area_insufficient CHECK (
        (has_sufficient_data = TRUE AND green_area_m2 IS NOT NULL AND delimitation_description IS NOT NULL AND affectation_type IS NOT NULL) OR
        (has_sufficient_data = FALSE AND green_area_m2 IS NULL AND delimitation_description IS NULL AND affectation_type IS NULL AND score_effect_pts IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS green_area_records_project_idx ON project_green_area_records(project_id);
CREATE INDEX IF NOT EXISTS green_area_records_code_idx ON project_green_area_records(project_code);

-- Ampliación de environmental_assessments para almacenar el dictamen y puntaje de áreas verdes
ALTER TABLE environmental_assessments
    ADD COLUMN IF NOT EXISTS green_area_json JSONB;

ALTER TABLE environmental_assessments
    ADD COLUMN IF NOT EXISTS environmental_score NUMERIC(5,2);

ALTER TABLE environmental_assessments
    ADD COLUMN IF NOT EXISTS score_explanation TEXT;
