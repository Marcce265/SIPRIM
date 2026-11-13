-- ============================================================================
-- SIPRIM: Procedimientos Almacenados para Pruebas de Data Masiva y Métricas
-- Base de datos: platform_db (PostgreSQL)
-- Uso: Ejecución de carga masiva (500 a 1000 expedientes) y cálculo de métricas
-- ============================================================================

CREATE TABLE IF NOT EXISTS batch_benchmark_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requested_count INTEGER NOT NULL,
    processed_count INTEGER NOT NULL,
    elapsed_ms NUMERIC(12, 2) NOT NULL,
    throughput_tps NUMERIC(12, 2) NOT NULL,
    high_risk_count INTEGER NOT NULL,
    medium_risk_count INTEGER NOT NULL,
    low_risk_count INTEGER NOT NULL,
    avg_budget_pen NUMERIC(14, 2) NOT NULL,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE PROCEDURE sp_cargar_evaluacion_masiva(
    IN p_cantidad INTEGER,
    OUT p_procesados INTEGER,
    OUT p_tiempo_ms NUMERIC
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_inicio TIMESTAMPTZ := clock_timestamp();
    v_i INTEGER;
    v_presupuesto NUMERIC(14, 2);
    v_prob NUMERIC(6, 4);
    v_alto INTEGER := 0;
    v_medio INTEGER := 0;
    v_bajo INTEGER := 0;
    v_suma_presupuesto NUMERIC(18, 2) := 0;
BEGIN
    p_procesados := 0;

    FOR v_i IN 1..p_cantidad LOOP
        v_presupuesto := ROUND((120000 + RANDOM() * 4800000)::NUMERIC, 2);
        v_prob := ROUND((0.12 + RANDOM() * 0.68)::NUMERIC, 4);
        v_suma_presupuesto := v_suma_presupuesto + v_presupuesto;

        IF v_prob >= 0.50 THEN
            v_alto := v_alto + 1;
        ELSIF v_prob >= 0.35 THEN
            v_medio := v_medio + 1;
        ELSE
            v_bajo := v_bajo + 1;
        END IF;

        p_procesados := p_procesados + 1;
    END LOOP;

    p_tiempo_ms := ROUND((EXTRACT(EPOCH FROM (clock_timestamp() - v_inicio)) * 1000)::NUMERIC, 2);

    INSERT INTO batch_benchmark_runs (
        requested_count,
        processed_count,
        elapsed_ms,
        throughput_tps,
        high_risk_count,
        medium_risk_count,
        low_risk_count,
        avg_budget_pen
    ) VALUES (
        p_cantidad,
        p_procesados,
        p_tiempo_ms,
        CASE WHEN p_tiempo_ms > 0 THEN ROUND((p_procesados / (p_tiempo_ms / 1000.0))::NUMERIC, 2) ELSE 0 END,
        v_alto,
        v_medio,
        v_bajo,
        ROUND((v_suma_presupuesto / GREATEST(p_procesados, 1))::NUMERIC, 2)
    );
END;
$$;
