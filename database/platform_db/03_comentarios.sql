-- Descripciones en espanol (los nombres siguen en ingles, segun el documento oficial)
COMMENT ON TABLE projects IS 'Proyectos de inversion registrados';
COMMENT ON COLUMN projects.id IS 'Identificador unico del proyecto';
COMMENT ON COLUMN projects.code IS 'Codigo del proyecto';
COMMENT ON COLUMN projects.created_by_user_id IS 'Usuario que lo registro (referencia a auth_db, sin FK)';
COMMENT ON COLUMN projects.status IS 'Estado: draft=borrador, ready=listo, evaluating=evaluando, evaluated=evaluado, error';
COMMENT ON COLUMN projects.created_at IS 'Fecha de registro';
COMMENT ON COLUMN projects.updated_at IS 'Fecha de ultima actualizacion';

COMMENT ON TABLE project_versions IS 'Versiones del expediente (corregir crea una version nueva)';
COMMENT ON COLUMN project_versions.id IS 'Identificador de la version';
COMMENT ON COLUMN project_versions.project_id IS 'Proyecto al que pertenece';
COMMENT ON COLUMN project_versions.version_number IS 'Numero de version (1, 2, 3...)';
COMMENT ON COLUMN project_versions.title IS 'Titulo del proyecto';
COMMENT ON COLUMN project_versions.description IS 'Descripcion';
COMMENT ON COLUMN project_versions.location_description IS 'Ubicacion territorial declarada por el planificador';
COMMENT ON COLUMN project_versions.proposed_land_use IS 'Uso de suelo o uso funcional propuesto';
COMMENT ON COLUMN project_versions.territorial_data_origin IS 'Origen del dato territorial: declarado, simulado o publico';
COMMENT ON COLUMN project_versions.estimated_budget_pen IS 'Presupuesto estimado en soles (S/)';
COMMENT ON COLUMN project_versions.beneficiaries_count IS 'Numero de beneficiarios';
COMMENT ON COLUMN project_versions.created_by_user_id IS 'Usuario que creo la version (referencia a auth_db)';
COMMENT ON COLUMN project_versions.created_at IS 'Fecha de creacion de la version';

COMMENT ON TABLE zoning_review_requests IS 'Solicitudes de prevalidacion territorial HU1.11; no son una aprobacion municipal';
COMMENT ON COLUMN zoning_review_requests.compatible IS 'Conclusion de compatibilidad; debe ser nula si no existe evidencia trazable';
COMMENT ON COLUMN zoning_review_requests.source_document IS 'Documento PDU/PDM que sustenta una conclusion';
COMMENT ON COLUMN zoning_review_requests.source_version IS 'Version o vigencia de la fuente territorial';
COMMENT ON COLUMN zoning_review_requests.source_locator IS 'Pagina, seccion, plano o codigo localizador';
COMMENT ON COLUMN zoning_review_requests.source_excerpt IS 'Fragmento verificable que sustenta el hallazgo';
COMMENT ON COLUMN zoning_review_requests.limitations IS 'Limites conocidos de la prevalidacion';

COMMENT ON TABLE criteria_versions IS 'Versiones de la politica de criterios de evaluacion';
COMMENT ON COLUMN criteria_versions.id IS 'Identificador de la politica';
COMMENT ON COLUMN criteria_versions.version_number IS 'Numero de version';
COMMENT ON COLUMN criteria_versions.status IS 'Estado: draft=borrador, active=activa, retired=retirada';
COMMENT ON COLUMN criteria_versions.excellent_cost_pen IS 'Costo por persona considerado excelente (100 puntos)';
COMMENT ON COLUMN criteria_versions.unacceptable_cost_pen IS 'Costo por persona considerado inaceptable (0 puntos)';
COMMENT ON COLUMN criteria_versions.created_by_user_id IS 'Administrador que la creo (referencia a auth_db)';
COMMENT ON COLUMN criteria_versions.created_at IS 'Fecha de creacion';
COMMENT ON COLUMN criteria_versions.activated_at IS 'Fecha de activacion';

COMMENT ON TABLE criterion_weights IS 'Peso de cada criterio dentro de una politica (deben sumar 100 %)';
COMMENT ON COLUMN criterion_weights.criteria_version_id IS 'Politica a la que pertenece';
COMMENT ON COLUMN criterion_weights.criterion_code IS 'Criterio (ECONOMIC = economico)';
COMMENT ON COLUMN criterion_weights.weight_percent IS 'Peso en porcentaje';

COMMENT ON TABLE evaluations IS 'Evaluaciones solicitadas';
COMMENT ON COLUMN evaluations.id IS 'Identificador de la evaluacion';
COMMENT ON COLUMN evaluations.project_version_id IS 'Version del expediente evaluada';
COMMENT ON COLUMN evaluations.criteria_version_id IS 'Politica de criterios usada';
COMMENT ON COLUMN evaluations.requested_by_user_id IS 'Planificador que la solicito (referencia a auth_db)';
COMMENT ON COLUMN evaluations.status IS 'Estado: queued=en cola, processing=procesando, completed=completada, failed=fallida';
COMMENT ON COLUMN evaluations.idempotency_key IS 'Clave para no duplicar la misma solicitud';
COMMENT ON COLUMN evaluations.requested_at IS 'Fecha de solicitud';
COMMENT ON COLUMN evaluations.started_at IS 'Fecha de inicio del procesamiento';
COMMENT ON COLUMN evaluations.finished_at IS 'Fecha de fin';
COMMENT ON COLUMN evaluations.error_message IS 'Mensaje de error, si fallo';

COMMENT ON TABLE economic_result_projections IS 'Copia del resultado economico para mostrarlo y ordenar (el detalle esta en economic_db)';
COMMENT ON COLUMN economic_result_projections.evaluation_id IS 'Evaluacion a la que corresponde';
COMMENT ON COLUMN economic_result_projections.economic_assessment_id IS 'Resultado original en economic_db (sin FK)';
COMMENT ON COLUMN economic_result_projections.cost_per_beneficiary_pen IS 'Costo por beneficiario en soles';
COMMENT ON COLUMN economic_result_projections.score_0_100 IS 'Puntaje economico de 0 a 100';
COMMENT ON COLUMN economic_result_projections.status IS 'Estado del resultado';
COMMENT ON COLUMN economic_result_projections.explanation IS 'Explicacion del calculo';
COMMENT ON COLUMN economic_result_projections.algorithm_version IS 'Version del algoritmo usado';
COMMENT ON COLUMN economic_result_projections.received_at IS 'Fecha en que se recibio el resultado';

COMMENT ON TABLE audit_events IS 'Historial de auditoria (la aplicacion solo puede insertar)';
COMMENT ON COLUMN audit_events.id IS 'Numero correlativo del evento';
COMMENT ON COLUMN audit_events.actor_user_id IS 'Usuario que hizo la accion (vacio = el sistema)';
COMMENT ON COLUMN audit_events.action IS 'Accion realizada';
COMMENT ON COLUMN audit_events.entity_type IS 'Tipo de registro afectado';
COMMENT ON COLUMN audit_events.entity_id IS 'Registro afectado';
COMMENT ON COLUMN audit_events.details IS 'Detalle de la accion';
COMMENT ON COLUMN audit_events.occurred_at IS 'Fecha y hora';

COMMENT ON TABLE outbox_events IS 'Bandeja de salida: eventos pendientes de enviar a otros servicios';
COMMENT ON COLUMN outbox_events.id IS 'Identificador del evento';
COMMENT ON COLUMN outbox_events.event_type IS 'Tipo de evento';
COMMENT ON COLUMN outbox_events.aggregate_id IS 'Registro al que se refiere';
COMMENT ON COLUMN outbox_events.payload IS 'Contenido del mensaje';
COMMENT ON COLUMN outbox_events.created_at IS 'Fecha de creacion';
COMMENT ON COLUMN outbox_events.published_at IS 'Fecha de envio (vacio = pendiente)';
COMMENT ON COLUMN outbox_events.publish_attempts IS 'Intentos de envio';

COMMENT ON TABLE inbox_events IS 'Bandeja de entrada: eventos ya recibidos (evita procesarlos dos veces)';
COMMENT ON COLUMN inbox_events.event_id IS 'Identificador del evento recibido';
COMMENT ON COLUMN inbox_events.received_at IS 'Fecha de recepcion';
