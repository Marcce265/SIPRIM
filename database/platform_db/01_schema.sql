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

CREATE TABLE IF NOT EXISTS project_versions (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    version_number INTEGER NOT NULL CHECK (version_number > 0),
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    estimated_budget_pen NUMERIC(18,2) NOT NULL CHECK (estimated_budget_pen > 0),
    beneficiaries_count INTEGER NOT NULL CHECK (beneficiaries_count > 0),
    created_by_user_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, version_number)
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
CREATE INDEX IF NOT EXISTS evaluations_status_idx ON evaluations(status, requested_at);
CREATE INDEX IF NOT EXISTS evaluations_version_idx ON evaluations(project_version_id, requested_at DESC);
CREATE INDEX IF NOT EXISTS audit_entity_idx ON audit_events(entity_type, entity_id, occurred_at);
CREATE INDEX IF NOT EXISTS outbox_pending_idx ON outbox_events(created_at)
    WHERE published_at IS NULL;
