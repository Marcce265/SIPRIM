-- =========================================================
-- SIPRIM - Migracion 01
-- Uso: base que YA tiene la tabla proyectos creada con schema.sql anterior.
-- Cambios: permite borradores (HU1.2) y agrega tablas de evaluaciones (HU1.3, HU1.10/1.11)
-- =========================================================

-- 1. Permitir proyectos incompletos (HU1.2)
ALTER TABLE proyectos
    ALTER COLUMN descripcion   DROP NOT NULL,
    ALTER COLUMN ubicacion     DROP NOT NULL,
    ALTER COLUMN presupuesto   DROP NOT NULL,
    ALTER COLUMN beneficiarios DROP NOT NULL,
    ALTER COLUMN tipo_proyecto DROP NOT NULL;

-- 2. Resultados del Agente Economico (HU1.3)
CREATE TABLE IF NOT EXISTS evaluaciones_economicas (
    id                     SERIAL        PRIMARY KEY,
    proyecto_id            INTEGER       NOT NULL UNIQUE REFERENCES proyectos(id),
    presupuesto            NUMERIC(18,2) NOT NULL,
    beneficiarios          INTEGER       NOT NULL,
    costo_por_habitante    NUMERIC(18,2) NOT NULL,
    retorno_socioeconomico NUMERIC(18,2),
    estado_evaluacion      VARCHAR(30)   NOT NULL,
    pendientes             JSON          NOT NULL,
    fecha_evaluacion       TIMESTAMPTZ   NOT NULL
);

-- 3. Resultados del Agente Juridico (HU1.10 / HU1.11)
CREATE TABLE IF NOT EXISTS evaluaciones_juridicas (
    id               SERIAL      PRIMARY KEY,
    proyecto_id      INTEGER     NOT NULL UNIQUE REFERENCES proyectos(id),
    estado           VARCHAR(50) NOT NULL,
    cumple           BOOLEAN,
    observaciones    JSON        NOT NULL,
    fuentes          JSON        NOT NULL,
    fecha_evaluacion TIMESTAMPTZ NOT NULL
);
