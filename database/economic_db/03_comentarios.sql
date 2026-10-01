-- Descripciones en espanol (los nombres siguen en ingles, segun el documento oficial)
COMMENT ON TABLE economic_assessments IS 'Evaluaciones economicas calculadas por el agente economico';
COMMENT ON COLUMN economic_assessments.id IS 'Identificador de la evaluacion economica';
COMMENT ON COLUMN economic_assessments.evaluation_id IS 'Evaluacion solicitada en platform_db (sin FK)';
COMMENT ON COLUMN economic_assessments.project_version_id IS 'Version del expediente (referencia a platform_db)';
COMMENT ON COLUMN economic_assessments.criteria_version_id IS 'Politica de criterios usada (referencia a platform_db)';
COMMENT ON COLUMN economic_assessments.budget_snapshot_pen IS 'Presupuesto recibido en soles (copia fija)';
COMMENT ON COLUMN economic_assessments.beneficiaries_snapshot IS 'Beneficiarios recibidos (copia fija)';
COMMENT ON COLUMN economic_assessments.excellent_cost_snapshot_pen IS 'Umbral excelente usado (copia fija)';
COMMENT ON COLUMN economic_assessments.unacceptable_cost_snapshot_pen IS 'Umbral inaceptable usado (copia fija)';
COMMENT ON COLUMN economic_assessments.cost_per_beneficiary_pen IS 'Costo por beneficiario = presupuesto / beneficiarios';
COMMENT ON COLUMN economic_assessments.score_0_100 IS 'Puntaje economico de 0 a 100';
COMMENT ON COLUMN economic_assessments.status IS 'Estado del calculo';
COMMENT ON COLUMN economic_assessments.explanation IS 'Explicacion del calculo';
COMMENT ON COLUMN economic_assessments.algorithm_version IS 'Version del algoritmo';
COMMENT ON COLUMN economic_assessments.created_at IS 'Fecha de creacion';
COMMENT ON COLUMN economic_assessments.completed_at IS 'Fecha de finalizacion';

COMMENT ON TABLE assessment_metrics IS 'Indicadores de cada evaluacion economica';
COMMENT ON COLUMN assessment_metrics.id IS 'Identificador del indicador';
COMMENT ON COLUMN assessment_metrics.assessment_id IS 'Evaluacion economica a la que pertenece';
COMMENT ON COLUMN assessment_metrics.metric_code IS 'Codigo del indicador';
COMMENT ON COLUMN assessment_metrics.numeric_value IS 'Valor calculado';
COMMENT ON COLUMN assessment_metrics.unit IS 'Unidad';
COMMENT ON COLUMN assessment_metrics.formula IS 'Formula usada';

COMMENT ON TABLE processed_requests IS 'Solicitudes ya procesadas (evita calcular dos veces)';
COMMENT ON COLUMN processed_requests.event_id IS 'Evento recibido';
COMMENT ON COLUMN processed_requests.evaluation_id IS 'Evaluacion solicitada';
COMMENT ON COLUMN processed_requests.assessment_id IS 'Resultado generado';
COMMENT ON COLUMN processed_requests.processed_at IS 'Fecha de procesamiento';
