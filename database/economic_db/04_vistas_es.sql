CREATE OR REPLACE VIEW vista_resultados_economicos AS
SELECT budget_snapshot_pen AS presupuesto_soles, beneficiaries_snapshot AS beneficiarios,
       cost_per_beneficiary_pen AS costo_por_persona, score_0_100 AS puntaje,
       explanation AS explicacion, algorithm_version AS algoritmo, completed_at AS calculado_en
FROM economic_assessments;

CREATE OR REPLACE VIEW vista_indicadores AS
SELECT a.budget_snapshot_pen AS presupuesto_soles,
       CASE m.metric_code WHEN 'COST_PER_BENEFICIARY' THEN 'Costo por beneficiario'
                          WHEN 'ECONOMIC_SCORE' THEN 'Puntaje económico' ELSE m.metric_code END AS indicador,
       m.numeric_value AS valor, m.unit AS unidad, m.formula AS formula
FROM assessment_metrics m JOIN economic_assessments a ON a.id = m.assessment_id;
