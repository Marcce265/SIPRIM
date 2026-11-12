-- ============================================================================
-- SIPRIM: Procedimientos Almacenados (Stored Procedures) - Unidad 3 / Semana 12
-- Base de datos: platform_db
-- Arquitectura: Hexagonal con persistencia relacional en PostgreSQL
-- ============================================================================

-- Tabla para persistencia y auditoría de inferencias de Machine Learning
CREATE TABLE IF NOT EXISTS ml_prediction_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    expediente_code VARCHAR(32) NOT NULL,
    monto_inversion NUMERIC(14, 2) NOT NULL,
    beneficiarios INTEGER NOT NULL,
    plazo_dias INTEGER NOT NULL,
    probabilidad_sobrecosto NUMERIC(5, 4) NOT NULL,
    nivel_riesgo_sobrecosto VARCHAR(16) NOT NULL,
    sobrecosto_estimado_pct NUMERIC(5, 2) NOT NULL,
    clase_viabilidad_plazo VARCHAR(32) NOT NULL,
    retraso_estimado_dias INTEGER NOT NULL,
    modelo_version VARCHAR(64) NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ml_prediction_logs_code ON ml_prediction_logs(expediente_code);
CREATE INDEX IF NOT EXISTS idx_ml_prediction_logs_project ON ml_prediction_logs(project_id);


-- ----------------------------------------------------------------------------
-- Procedimiento 1: Inserción y Procesamiento Masivo Transaccional (500 a 1000 registros)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_registrar_evaluacion_masiva(
    IN p_cantidad INTEGER,
    OUT p_total_procesados INTEGER,
    OUT p_tiempo_ms NUMERIC
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_inicio TIMESTAMPTZ := clock_timestamp();
    v_i INTEGER;
    v_code VARCHAR(32);
    v_proj_id UUID;
    v_monto NUMERIC(14,2);
    v_benef INTEGER;
    v_plazo INTEGER;
    v_prob_sc NUMERIC(5,4);
    v_nivel_sc VARCHAR(16);
    v_sc_pct NUMERIC(5,2);
    v_clase_plazo VARCHAR(32);
    v_retraso INTEGER;
BEGIN
    p_total_procesados := 0;

    FOR v_i IN 1..p_cantidad LOOP
        v_code := 'EXP-MASIVO-' || LPAD(v_i::TEXT, 5, '0');
        v_monto := ROUND((100000 + (RANDOM() * 2500000))::NUMERIC, 2);
        v_benef := 200 + FLOOR(RANDOM() * 15000)::INTEGER;
        v_plazo := 60 + FLOOR(RANDOM() * 300)::INTEGER;

        -- Regla inferencial de riesgo integrada en el SP
        v_prob_sc := ROUND((0.15 + (RANDOM() * 0.75))::NUMERIC, 4);
        IF v_prob_sc >= 0.65 THEN
            v_nivel_sc := 'ALTO';
            v_sc_pct := ROUND((12.0 + (v_prob_sc * 18.0))::NUMERIC, 2);
            v_clase_plazo := 'CRITICO';
            v_retraso := 90 + FLOOR(RANDOM() * 120)::INTEGER;
        ELSIF v_prob_sc >= 0.35 THEN
            v_nivel_sc := 'MEDIO';
            v_sc_pct := ROUND((5.0 + (v_prob_sc * 10.0))::NUMERIC, 2);
            v_clase_plazo := 'RIESGO_MODERADO';
            v_retraso := 30 + FLOOR(RANDOM() * 50)::INTEGER;
        ELSE
            v_nivel_sc := 'BAJO';
            v_sc_pct := ROUND((v_prob_sc * 4.0)::NUMERIC, 2);
            v_clase_plazo := 'VIABLE';
            v_retraso := FLOOR(RANDOM() * 20)::INTEGER;
        END IF;

        -- Registrar log predictivo
        INSERT INTO ml_prediction_logs (
            project_id,
            expediente_code,
            monto_inversion,
            beneficiarios,
            plazo_dias,
            probabilidad_sobrecosto,
            nivel_riesgo_sobrecosto,
            sobrecosto_estimado_pct,
            clase_viabilidad_plazo,
            retraso_estimado_dias,
            modelo_version
        ) VALUES (
            NULL,
            v_code,
            v_monto,
            v_benef,
            v_plazo,
            v_prob_sc,
            v_nivel_sc,
            v_sc_pct,
            v_clase_plazo,
            v_retraso,
            'RandomForest_v1.2.0_GradientBoosting_v1.1.0'
        );

        p_total_procesados := p_total_procesados + 1;
    END LOOP;

    p_tiempo_ms := ROUND((EXTRACT(EPOCH FROM (clock_timestamp() - v_inicio)) * 1000)::NUMERIC, 2);
END;
$$;


-- ----------------------------------------------------------------------------
-- Procedimiento 2: Inferencia de Riesgo y Actualización Atómica por Expediente
-- ----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_evaluar_expediente_ml(
    IN p_project_id UUID,
    IN p_expediente_code VARCHAR(32),
    IN p_monto NUMERIC,
    IN p_beneficiarios INTEGER,
    IN p_plazo_dias INTEGER,
    IN p_prob_sobrecosto NUMERIC,
    IN p_nivel_riesgo VARCHAR,
    IN p_sobrecosto_pct NUMERIC,
    IN p_clase_viabilidad VARCHAR,
    IN p_retraso_dias INTEGER,
    OUT p_log_id UUID
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO ml_prediction_logs (
        project_id,
        expediente_code,
        monto_inversion,
        beneficiarios,
        plazo_dias,
        probabilidad_sobrecosto,
        nivel_riesgo_sobrecosto,
        sobrecosto_estimado_pct,
        clase_viabilidad_plazo,
        retraso_estimado_dias,
        modelo_version
    ) VALUES (
        p_project_id,
        p_expediente_code,
        p_monto,
        p_beneficiarios,
        p_plazo_dias,
        p_prob_sobrecosto,
        p_nivel_riesgo,
        p_sobrecosto_pct,
        p_clase_viabilidad,
        p_retraso_dias,
        'RandomForest_v1.2.0'
    )
    RETURNING id INTO p_log_id;
END;
$$;


-- ----------------------------------------------------------------------------
-- Procedimiento 3: Resumen Estadístico y Métricas de Cartera Predictiva
-- ----------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE sp_resumen_metricas_ml(
    OUT p_total_evaluados INTEGER,
    OUT p_proyectos_alto_riesgo INTEGER,
    OUT p_proyectos_viables INTEGER,
    OUT p_costo_promedio NUMERIC,
    OUT p_sobrecosto_promedio_pct NUMERIC
)
LANGUAGE plpgsql
AS $$
BEGIN
    SELECT
        COUNT(*),
        COUNT(*) FILTER (WHERE nivel_riesgo_sobrecosto = 'ALTO'),
        COUNT(*) FILTER (WHERE clase_viabilidad_plazo = 'VIABLE'),
        ROUND(AVG(monto_inversion), 2),
        ROUND(AVG(sobrecosto_estimado_pct), 2)
    INTO
        p_total_evaluados,
        p_proyectos_alto_riesgo,
        p_proyectos_viables,
        p_costo_promedio,
        p_sobrecosto_promedio_pct
    FROM ml_prediction_logs;
END;
$$;
