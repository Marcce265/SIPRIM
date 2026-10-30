-- =========================================================
-- PMV 2 - Sprint 2 - HU1.6: Migración de Evaluación de Impacto Ambiental
-- Idempotente para instalaciones nuevas o volúmenes existentes.
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
    is_in_protected_or_risk_area BOOLEAN NOT NULL DEFAULT FALSE,
    source_name VARCHAR(240) NOT NULL,
    data_origin VARCHAR(16) NOT NULL DEFAULT 'simulated'
        CHECK (data_origin IN ('declared', 'simulated', 'public')),
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_env_insufficient_no_evidence CHECK (
        (has_sufficient_data = TRUE AND verifiable_evidence IS NOT NULL) OR
        (has_sufficient_data = FALSE AND verifiable_evidence IS NULL)
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

-- Inserción de PRY-C si no existe
INSERT INTO projects (id, code, created_by_user_id, status) VALUES
    ('a0000000-0000-4000-a000-00000000000c', 'PRY-C', '10000000-0000-4000-a000-000000000002', 'ready')
ON CONFLICT (code) DO NOTHING;

INSERT INTO project_versions (id, project_id, version_number, title, description, location_description,
                              proposed_land_use, territorial_data_origin, estimated_budget_pen,
                              beneficiaries_count, created_by_user_id) VALUES
    ('b0000000-0000-4000-a000-00000000000c', 'a0000000-0000-4000-a000-00000000000c', 1,
     'Proyecto C - Taller de maestranza y depósito municipal (prueba)', 'Dato ficticio para el PMV 2 (HU1.6)',
     'CASO SIMULADO - Faja marginal del Río Shullcas - El Tambo', 'taller / maestranza', 'simulated', 350000.00, 1200,
     '10000000-0000-4000-a000-000000000002')
ON CONFLICT (project_id, version_number) DO NOTHING;

-- Semillas de datos ambientales territoriales
INSERT INTO project_environmental_records
    (id, project_id, project_code, has_sufficient_data, environmental_component,
     declared_impacts, declared_measures, verifiable_evidence, proximity_to_water_meters,
     is_in_protected_or_risk_area, source_name, data_origin, description)
VALUES
    -- PRY-A (Impacto moderado/bajo con sustento y mitigaciones)
    ('81000000-0000-4000-a000-000000000001', 'a0000000-0000-4000-a000-00000000000a', 'PRY-A', TRUE,
     'aire_acustico_residuos',
     'El expediente declara generación temporal de polvo, ruido diurno durante obras preliminares y demolición de pavimento deteriorado.',
     'Aspersión de agua diaria para control de material particulado, cerco perimétrico con malla antipolvo y horario de trabajo restringido de 08:00 a 17:00 h.',
     'Ubicación en trama urbana consolidada de El Tambo. Distancia superior a 400 m de fajas marginales o cursos hídricos; fuera de áreas naturales protegidas o de conservación (PDM Huancayo / CENEPRED-SIGRID).',
     420.00, FALSE,
     'Dataset ambiental simulado SIPRIM El Tambo - PDM Huancayo / CENEPRED (Simulado)', 'simulated',
     'Losa deportiva en área consolidada. Impactos menores y mitigables mediante buenas prácticas de obra civil.'),

    -- PRY-C (Riesgo ambiental ALTO: Faja marginal del Río Shullcas)
    ('81000000-0000-4000-a000-000000000002', 'a0000000-0000-4000-a000-00000000000c', 'PRY-C', TRUE,
     'recurso_hidrico_ecosistema',
     'El administrado declara almacenamiento temporal de vehículos y depósito de materiales sin vertimientos contaminantes a la quebrada.',
     'Piso de afirmado compacto y cuneta perimétrica rústica sin trampa de grasas ni canalización certificada.',
     'Predio emplazado a 25 metros de la faja marginal del Río Shullcas. Zona clasificada como de muy alto riesgo no mitigable e intangible por el PDM Huancayo 2017-2037 (O.M. N.° 636-MPH) y Ley 29664 (SINAGERD); riesgo crítico de escorrentía con hidrocarburos y alteración del ecosistema ribereño.',
     25.00, TRUE,
     'Dataset ambiental simulado SIPRIM El Tambo - PDM Huancayo / ANA-ALA Mantaro / SIGRID (Simulado)', 'simulated',
     'Instalación de maestranza en faja marginal. Riesgo severo de contaminación fluvial y afectación hidrológica no mitigable.'),

    -- PRY-B (Información ambiental insuficiente: falta DIA y línea base)
    ('81000000-0000-4000-a000-000000000003', 'a0000000-0000-4000-a000-00000000000b', 'PRY-B', FALSE,
     'integral',
     NULL,
     NULL,
     NULL,
     NULL, FALSE,
     'Catastro Municipal El Tambo (Sin Declaración de Impacto Ambiental ni línea base registrada)', 'simulated',
     'Información insuficiente')
ON CONFLICT (id) DO UPDATE SET
    declared_impacts = EXCLUDED.declared_impacts,
    declared_measures = EXCLUDED.declared_measures,
    verifiable_evidence = EXCLUDED.verifiable_evidence,
    proximity_to_water_meters = EXCLUDED.proximity_to_water_meters,
    is_in_protected_or_risk_area = EXCLUDED.is_in_protected_or_risk_area,
    source_name = EXCLUDED.source_name,
    data_origin = EXCLUDED.data_origin,
    description = EXCLUDED.description;
