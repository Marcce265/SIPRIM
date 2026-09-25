-- Esquema SIPRIM para PostgreSQL (local / Neon / Supabase)
-- Alineado con backend/infrastructure/output/database/models.py

CREATE TABLE IF NOT EXISTS proyectos (
    id             SERIAL        PRIMARY KEY,
    nombre         VARCHAR(200)  NOT NULL,
    descripcion    TEXT          NOT NULL,
    ubicacion      VARCHAR(300)  NOT NULL,
    presupuesto    NUMERIC(18,2) NOT NULL CHECK (presupuesto > 0),
    beneficiarios  INTEGER       NOT NULL CHECK (beneficiarios > 0),
    tipo_proyecto  VARCHAR(150)  NOT NULL,
    estado         VARCHAR(30)   NOT NULL DEFAULT 'REGISTRADO',
    fecha_creacion TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_proyectos_estado ON proyectos (estado);

-- Evaluación económica (HU posterior)
CREATE TABLE IF NOT EXISTS evaluaciones_economicas (
    id                      SERIAL        PRIMARY KEY,
    proyecto_id             INTEGER       NOT NULL UNIQUE REFERENCES proyectos (id) ON DELETE CASCADE,
    presupuesto             NUMERIC(18,2) NOT NULL,
    beneficiarios           INTEGER       NOT NULL,
    costo_por_habitante     NUMERIC(18,2) NOT NULL,
    retorno_socioeconomico  NUMERIC(18,2),
    estado_evaluacion       VARCHAR(30)   NOT NULL,
    pendientes              JSON          NOT NULL DEFAULT '[]',
    fecha_evaluacion        TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_eval_economica_proyecto ON evaluaciones_economicas (proyecto_id);

-- Evaluación jurídica (HU posterior)
CREATE TABLE IF NOT EXISTS evaluaciones_juridicas (
    id                SERIAL       PRIMARY KEY,
    proyecto_id       INTEGER      NOT NULL UNIQUE REFERENCES proyectos (id) ON DELETE CASCADE,
    estado            VARCHAR(50)  NOT NULL,
    cumple            BOOLEAN,
    observaciones     JSON         NOT NULL DEFAULT '[]',
    fuentes           JSON         NOT NULL DEFAULT '[]',
    fecha_evaluacion  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_eval_juridica_proyecto ON evaluaciones_juridicas (proyecto_id);
