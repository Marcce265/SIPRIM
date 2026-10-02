-- =========================================================
-- PMV 1 · ms-platform · base platform_db
-- Fuente: BASES_DE_DATOS_PMV1_MICROSERVICIOS.md, seccion 8.2
-- Ejecutar SOLO en platform_db. Se puede ejecutar varias veces.
-- Los *_user_id son UUID de ms-auth: SIN foreign key entre bases.
-- =========================================================
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY,
    code VARCHAR(40) NOT NULL UNIQUE,
    created_by_user_id UUID NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT projects_status_check CHECK (status IN ('draft','ready','evaluating','evaluated','error'))
);

-- Migracion idempotente para instalaciones creadas antes de HU1.11.
ALTER TABLE IF EXISTS project_versions
    ADD COLUMN IF NOT EXISTS location_description VARCHAR(300),
    ADD COLUMN IF NOT EXISTS proposed_land_use VARCHAR(150),
    ADD COLUMN IF NOT EXISTS territorial_data_origin VARCHAR(16) NOT NULL DEFAULT 'declared';

CREATE TABLE IF NOT EXISTS project_versions (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    version_number INTEGER NOT NULL CHECK (version_number > 0),
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    location_description VARCHAR(300),
    proposed_land_use VARCHAR(150),
    territorial_data_origin VARCHAR(16) NOT NULL DEFAULT 'declared'
        CHECK (territorial_data_origin IN ('declared','simulated','public')),
    estimated_budget_pen NUMERIC(18,2) NOT NULL CHECK (estimated_budget_pen > 0),
    beneficiaries_count INTEGER NOT NULL CHECK (beneficiaries_count > 0),
    created_by_user_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, version_number)
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'project_versions_territorial_data_origin_check'
    ) THEN
        ALTER TABLE project_versions
        ADD CONSTRAINT project_versions_territorial_data_origin_check
        CHECK (territorial_data_origin IN ('declared','simulated','public'));
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS zoning_review_requests (
    id UUID PRIMARY KEY,
    project_version_id UUID NOT NULL REFERENCES project_versions(id) ON DELETE RESTRICT,
    requested_by_user_id UUID NOT NULL,
    idempotency_key VARCHAR(120) NOT NULL UNIQUE,
    status VARCHAR(24) NOT NULL DEFAULT 'requires_review'
        CHECK (status IN ('requires_review','evidence_available','reviewed')),
    compatible BOOLEAN,
    source_document VARCHAR(240),
    source_version VARCHAR(120),
    source_locator VARCHAR(160),
    source_excerpt TEXT,
    limitations TEXT NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_at TIMESTAMPTZ,
    CONSTRAINT zoning_conclusion_requires_evidence CHECK (
        compatible IS NULL OR (
            NULLIF(btrim(source_document), '') IS NOT NULL
            AND NULLIF(btrim(source_version), '') IS NOT NULL
            AND NULLIF(btrim(source_locator), '') IS NOT NULL
            AND NULLIF(btrim(source_excerpt), '') IS NOT NULL
        )
    ),
    CONSTRAINT zoning_pending_has_no_conclusion CHECK (
        status <> 'requires_review' OR compatible IS NULL
    )
);

CREATE TABLE IF NOT EXISTS criteria_versions (
    id UUID PRIMARY KEY,
    version_number INTEGER NOT NULL UNIQUE CHECK (version_number > 0),
    status VARCHAR(16) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft','active','retired')),
    excellent_cost_pen NUMERIC(18,2) NOT NULL CHECK (excellent_cost_pen > 0),
    unacceptable_cost_pen NUMERIC(18,2) NOT NULL,
    created_by_user_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    activated_at TIMESTAMPTZ,
    CONSTRAINT costs_order_check CHECK (unacceptable_cost_pen > excellent_cost_pen)
);
CREATE UNIQUE INDEX IF NOT EXISTS only_one_active_criteria ON criteria_versions(status)
    WHERE status = 'active';

CREATE TABLE IF NOT EXISTS criterion_weights (
    criteria_version_id UUID NOT NULL REFERENCES criteria_versions(id) ON DELETE RESTRICT,
    criterion_code VARCHAR(40) NOT NULL,
    weight_percent NUMERIC(5,2) NOT NULL CHECK (weight_percent >= 0 AND weight_percent <= 100),
    PRIMARY KEY (criteria_version_id, criterion_code)
);

CREATE TABLE IF NOT EXISTS evaluations (
    id UUID PRIMARY KEY,
    project_version_id UUID NOT NULL REFERENCES project_versions(id) ON DELETE RESTRICT,
    criteria_version_id UUID NOT NULL REFERENCES criteria_versions(id) ON DELETE RESTRICT,
    requested_by_user_id UUID NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued','processing','completed','failed')),
    idempotency_key VARCHAR(120) NOT NULL UNIQUE,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS economic_result_projections (
    evaluation_id UUID PRIMARY KEY REFERENCES evaluations(id) ON DELETE RESTRICT,
    economic_assessment_id UUID NOT NULL UNIQUE,
    cost_per_beneficiary_pen NUMERIC(18,2) NOT NULL CHECK (cost_per_beneficiary_pen >= 0),
    score_0_100 NUMERIC(5,2) NOT NULL CHECK (score_0_100 BETWEEN 0 AND 100),
    status VARCHAR(16) NOT NULL DEFAULT 'completed' CHECK (status = 'completed'),
    explanation TEXT NOT NULL,
    algorithm_version VARCHAR(40) NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_user_id UUID,
    action VARCHAR(80) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS outbox_events (
    id UUID PRIMARY KEY,
    event_type VARCHAR(80) NOT NULL,
    aggregate_id UUID NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at TIMESTAMPTZ,
    publish_attempts INTEGER NOT NULL DEFAULT 0 CHECK (publish_attempts >= 0)
);

CREATE TABLE IF NOT EXISTS inbox_events (
    event_id UUID PRIMARY KEY,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS versions_project_idx ON project_versions(project_id, version_number DESC);
CREATE INDEX IF NOT EXISTS zoning_reviews_project_idx ON zoning_review_requests(project_version_id, requested_at DESC);
CREATE INDEX IF NOT EXISTS evaluations_status_idx ON evaluations(status, requested_at);
CREATE INDEX IF NOT EXISTS evaluations_version_idx ON evaluations(project_version_id, requested_at DESC);
CREATE INDEX IF NOT EXISTS audit_entity_idx ON audit_events(entity_type, entity_id, occurred_at);
CREATE INDEX IF NOT EXISTS outbox_pending_idx ON outbox_events(created_at)
    WHERE published_at IS NULL;

-- =========================================================
-- HU2.1 / RF03 / RF12 · Corpus normativo versionado y trazabilidad de consultas
-- Fuentes referenciales didacticas para el Asesor Juridico
-- =========================================================
CREATE TABLE IF NOT EXISTS normative_documents (
    id VARCHAR(40) PRIMARY KEY,
    document_name VARCHAR(150) NOT NULL,
    short_code VARCHAR(40) NOT NULL,
    version VARCHAR(40) NOT NULL DEFAULT '2026-v1',
    topic VARCHAR(150) NOT NULL,
    content TEXT NOT NULL,
    in_force BOOLEAN NOT NULL DEFAULT TRUE,
    has_alert BOOLEAN NOT NULL DEFAULT FALSE,
    data_origin VARCHAR(24) NOT NULL DEFAULT 'simulated',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT normative_data_origin_check
        CHECK (data_origin IN ('declared', 'simulated', 'public', 'official'))
);

CREATE TABLE IF NOT EXISTS normative_search_logs (
    id UUID PRIMARY KEY,
    actor_user_id UUID NOT NULL,
    query TEXT NOT NULL,
    document_filter VARCHAR(150),
    results_count INTEGER NOT NULL CHECK (results_count >= 0),
    idempotency_key VARCHAR(120) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS normative_docs_lookup_idx ON normative_documents(document_name, in_force);
CREATE INDEX IF NOT EXISTS normative_docs_short_code_idx ON normative_documents(short_code);
CREATE INDEX IF NOT EXISTS normative_docs_topic_idx ON normative_documents(topic);
CREATE INDEX IF NOT EXISTS normative_search_actor_idx ON normative_search_logs(actor_user_id, created_at DESC);
