-- =========================================================
-- Consultas para ver los datos con columnas en espanol
-- Ejecutar cada bloque en la base indicada (SQL Editor de Neon)
-- =========================================================

-- ===== auth_db =====
-- Usuarios y sus roles
SELECT u.full_name AS nombre, u.email AS correo, r.name AS rol, u.is_active AS activo
FROM users u JOIN user_roles ur ON ur.user_id = u.id JOIN roles r ON r.id = ur.role_id;

-- ===== platform_db =====
-- Proyectos y su ultima version
SELECT p.code AS codigo, pv.title AS titulo, pv.version_number AS version,
       pv.estimated_budget_pen AS presupuesto_soles, pv.beneficiaries_count AS beneficiarios,
       p.status AS estado
FROM projects p JOIN project_versions pv ON pv.project_id = p.id
ORDER BY p.code, pv.version_number;

-- Evaluaciones y su resultado
SELECT pv.title AS proyecto, e.status AS estado, r.cost_per_beneficiary_pen AS costo_por_persona,
       r.score_0_100 AS puntaje, r.explanation AS explicacion
FROM evaluations e
JOIN project_versions pv ON pv.id = e.project_version_id
LEFT JOIN economic_result_projections r ON r.evaluation_id = e.id
ORDER BY r.score_0_100 DESC NULLS LAST;

-- Historial de auditoria
SELECT occurred_at AS fecha, action AS accion, entity_type AS tipo, details AS detalle
FROM audit_events ORDER BY occurred_at;

-- Prevalidaciones territoriales HU1.11
SELECT codigo_proyecto, version_expediente, estado, compatible,
       documento, version_fuente, localizador, limitaciones, solicitada_en
FROM vista_revisiones_zonificacion
ORDER BY solicitada_en DESC;

-- Fuentes normativas y alertas para el Asesor Juridico (HU2.1)
SELECT id_fragmento, documento, codigo_corto, version_norma, tema,
       tiene_alerta, origen_dato
FROM vista_fuentes_normativas
ORDER BY codigo_corto, id_fragmento;

-- Historial de busquedas normativas (HU2.1)
SELECT id_busqueda, consulta, filtro_documento, resultados_obtenidos, consultado_en
FROM vista_busquedas_normativas
ORDER BY consultado_en DESC;

-- ===== economic_db =====
-- Resultados del agente economico
SELECT budget_snapshot_pen AS presupuesto, beneficiaries_snapshot AS beneficiarios,
       cost_per_beneficiary_pen AS costo_por_persona, score_0_100 AS puntaje,
       algorithm_version AS algoritmo
FROM economic_assessments ORDER BY score_0_100 DESC;

-- ===== Cualquier base =====
-- Ver la descripcion en espanol de cada tabla y columna
SELECT c.table_name AS tabla, c.column_name AS columna,
       col_description((quote_ident(c.table_schema)||'.'||quote_ident(c.table_name))::regclass, c.ordinal_position) AS descripcion
FROM information_schema.columns c
WHERE c.table_schema = 'public'
ORDER BY c.table_name, c.ordinal_position;
