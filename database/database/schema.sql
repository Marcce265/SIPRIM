-- =========================================================
-- SIPRIM - Esquema de base de datos PostgreSQL (Neon)
-- Uso: base NUEVA (vacia). Equivale a backend/infrastructure/output/database/models.py
-- HU1.1 Registro | HU1.2 Validacion | HU1.3 Evaluacion economica | HU1.10/1.11 Evaluacion juridica
-- =========================================================

-- Expedientes de proyectos (HU1.1 / HU1.2)
-- Los campos pueden quedar vacios para guardar borradores incompletos (HU1.2)
CREATE TABLE IF NOT EXISTS proyectos (
    id             SERIAL        PRIMARY KEY,
    nombre         VARCHAR(200)  NOT NULL,
    descripcion    TEXT,
    ubicacion      VARCHAR(300),
    presupuesto    NUMERIC(18,2) CHECK (presupuesto > 0),
    beneficiarios  INTEGER       CHECK (beneficiarios > 0),
    tipo_proyecto  VARCHAR(150),
    estado         VARCHAR(30)   NOT NULL DEFAULT 'REGISTRADO',  -- BORRADOR | REGISTRADO
    fecha_creacion TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- Resultados del Agente Economico (HU1.3)
CREATE TABLE IF NOT EXISTS evaluaciones_economicas (
    id                     SERIAL        PRIMARY KEY,
    proyecto_id            INTEGER       NOT NULL UNIQUE REFERENCES proyectos(id),
    presupuesto            NUMERIC(18,2) NOT NULL,
    beneficiarios          INTEGER       NOT NULL,
    costo_por_habitante    NUMERIC(18,2) NOT NULL,
    retorno_socioeconomico NUMERIC(18,2),
    estado_evaluacion      VARCHAR(30)   NOT NULL,              -- PARCIAL
    pendientes             JSON          NOT NULL,
    fecha_evaluacion       TIMESTAMPTZ   NOT NULL
);

-- Resultados del Agente Juridico (HU1.10 / HU1.11)
CREATE TABLE IF NOT EXISTS evaluaciones_juridicas (
    id               SERIAL      PRIMARY KEY,
    proyecto_id      INTEGER     NOT NULL UNIQUE REFERENCES proyectos(id),
    estado           VARCHAR(50) NOT NULL,                      -- PENDIENTE_VALIDACION_NORMATIVA
    cumple           BOOLEAN,
    observaciones    JSON        NOT NULL,
    fuentes          JSON        NOT NULL,
    fecha_evaluacion TIMESTAMPTZ NOT NULL
);
