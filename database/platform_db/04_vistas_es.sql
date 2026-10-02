CREATE OR REPLACE VIEW vista_proyectos AS
SELECT p.code AS codigo, pv.title AS titulo, pv.version_number AS version,
       pv.location_description AS ubicacion, pv.proposed_land_use AS uso_propuesto,
       pv.estimated_budget_pen AS presupuesto_soles, pv.beneficiaries_count AS beneficiarios,
       CASE p.status WHEN 'draft' THEN 'Borrador' WHEN 'ready' THEN 'Listo' WHEN 'evaluating' THEN 'Evaluando'
                     WHEN 'evaluated' THEN 'Evaluado' ELSE 'Error' END AS estado,
       pv.created_at AS registrado_en
FROM projects p JOIN project_versions pv ON pv.project_id = p.id;

CREATE OR REPLACE VIEW vista_revisiones_zonificacion AS
SELECT p.code AS codigo_proyecto, pv.version_number AS version_expediente,
       z.status AS estado, z.compatible AS compatible,
       z.source_document AS documento, z.source_version AS version_fuente,
       z.source_locator AS localizador, z.limitations AS limitaciones,
       z.requested_at AS solicitada_en
FROM zoning_review_requests z
JOIN project_versions pv ON pv.id = z.project_version_id
JOIN projects p ON p.id = pv.project_id;

CREATE OR REPLACE VIEW vista_evaluaciones AS
SELECT pv.title AS proyecto, pv.version_number AS version,
       CASE e.status WHEN 'queued' THEN 'En cola' WHEN 'processing' THEN 'Procesando'
                     WHEN 'completed' THEN 'Completada' ELSE 'Fallida' END AS estado,
       r.cost_per_beneficiary_pen AS costo_por_persona, r.score_0_100 AS puntaje,
       r.explanation AS explicacion, e.requested_at AS solicitada_en, e.finished_at AS terminada_en
FROM evaluations e
JOIN project_versions pv ON pv.id = e.project_version_id
LEFT JOIN economic_result_projections r ON r.evaluation_id = e.id;

CREATE OR REPLACE VIEW vista_criterios AS
SELECT cv.version_number AS version,
       CASE cv.status WHEN 'draft' THEN 'Borrador' WHEN 'active' THEN 'Activa' ELSE 'Retirada' END AS estado,
       cv.excellent_cost_pen AS costo_excelente, cv.unacceptable_cost_pen AS costo_inaceptable,
       CASE w.criterion_code WHEN 'ECONOMIC' THEN 'Económico' ELSE w.criterion_code END AS criterio,
       w.weight_percent AS peso_porcentaje
FROM criteria_versions cv JOIN criterion_weights w ON w.criteria_version_id = cv.id;

CREATE OR REPLACE VIEW vista_auditoria AS
SELECT occurred_at AS fecha,
       CASE action WHEN 'EVALUATION_REQUESTED' THEN 'Evaluación solicitada'
                   WHEN 'EVALUATION_COMPLETED' THEN 'Evaluación completada' ELSE action END AS accion,
       entity_type AS tipo, details AS detalle
FROM audit_events;
