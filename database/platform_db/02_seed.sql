-- =========================================================
-- PMV 1 · platform_db · datos semilla (ficticios)
-- Proyecto A: S/ 120 000 y 600 beneficiarios -> S/ 200 por persona
-- Proyecto B: S/  90 000 y 300 beneficiarios -> S/ 300 por persona
-- Politica activa v1: ECONOMIC = 100 %, excelente S/ 200, inaceptable S/ 500
-- created_by_user_id = UUID de las cuentas semilla de auth_db (sin FK)
-- =========================================================
INSERT INTO criteria_versions (id, version_number, status, excellent_cost_pen, unacceptable_cost_pen, created_by_user_id, activated_at)
VALUES ('c0000000-0000-4000-a000-000000000001', 1, 'active', 200.00, 500.00,
        '10000000-0000-4000-a000-000000000001', now())
ON CONFLICT (version_number) DO NOTHING;

INSERT INTO criterion_weights (criteria_version_id, criterion_code, weight_percent)
VALUES ('c0000000-0000-4000-a000-000000000001', 'ECONOMIC', 100.00)
ON CONFLICT DO NOTHING;

INSERT INTO projects (id, code, created_by_user_id, status) VALUES
    ('a0000000-0000-4000-a000-00000000000a', 'PRY-A', '10000000-0000-4000-a000-000000000002', 'ready'),
    ('a0000000-0000-4000-a000-00000000000b', 'PRY-B', '10000000-0000-4000-a000-000000000002', 'ready')
ON CONFLICT (code) DO NOTHING;

INSERT INTO project_versions (id, project_id, version_number, title, description, location_description,
                              proposed_land_use, territorial_data_origin, estimated_budget_pen,
                              beneficiaries_count, created_by_user_id) VALUES
    ('b0000000-0000-4000-a000-00000000000a', 'a0000000-0000-4000-a000-00000000000a', 1,
     'Proyecto A - Mejoramiento de losa deportiva (prueba)', 'Dato ficticio para el PMV 1',
     'CASO SIMULADO - distrito de El Tambo', 'recreacion', 'simulated', 120000.00, 600,
     '10000000-0000-4000-a000-000000000002'),
    ('b0000000-0000-4000-a000-00000000000b', 'a0000000-0000-4000-a000-00000000000b', 1,
     'Proyecto B - Ampliacion de veredas (prueba)', 'Dato ficticio para el PMV 1',
     'CASO SIMULADO - distrito de El Tambo', 'infraestructura vial', 'simulated', 90000.00, 300,
     '10000000-0000-4000-a000-000000000002')
ON CONFLICT (project_id, version_number) DO NOTHING;

UPDATE project_versions
SET location_description = 'CASO SIMULADO - distrito de El Tambo',
    proposed_land_use = CASE
        WHEN project_id = 'a0000000-0000-4000-a000-00000000000a' THEN 'recreacion'
        ELSE 'infraestructura vial'
    END,
    territorial_data_origin = 'simulated'
WHERE project_id IN (
    'a0000000-0000-4000-a000-00000000000a',
    'a0000000-0000-4000-a000-00000000000b'
) AND (location_description IS NULL OR proposed_land_use IS NULL);

-- =========================================================
-- HU2.1 / RF03 / RF12 · Datos semilla normativos didacticos (PoC PMV1)
-- 24 fragmentos normativos simulados para El Tambo, Huancayo
-- 6 por cada grupo normativo: Ley 27972, DL 1252, Ley 32069, PDU/PDM
-- PDUPDM-02 y PDUPDM-04 marcados con has_alert=TRUE (causales de alerta)
-- =========================================================
INSERT INTO normative_documents (id, document_name, short_code, version, topic, content, in_force, has_alert, data_origin) VALUES
    ('LEY27972-01', 'Ley N.° 27972', 'LEY_27972', '2026-v1', 'Competencias municipales',
     'Resumen didáctico simulado: las municipalidades ejercen competencias y funciones en asuntos de interés local dentro del marco legal correspondiente.', TRUE, FALSE, 'simulated'),
    ('LEY27972-02', 'Ley N.° 27972', 'LEY_27972', '2026-v1', 'Desarrollo urbano',
     'Resumen didáctico simulado: la gestión municipal comprende funciones vinculadas con organización del espacio físico y uso del suelo.', TRUE, FALSE, 'simulated'),
    ('LEY27972-03', 'Ley N.° 27972', 'LEY_27972', '2026-v1', 'Concejo municipal',
     'Resumen didáctico simulado: el concejo municipal cumple funciones normativas y fiscalizadoras dentro del gobierno local.', TRUE, FALSE, 'simulated'),
    ('LEY27972-04', 'Ley N.° 27972', 'LEY_27972', '2026-v1', 'Alcaldía',
     'Resumen didáctico simulado: la alcaldía ejerce funciones ejecutivas y de representación del gobierno local conforme a ley.', TRUE, FALSE, 'simulated'),
    ('LEY27972-05', 'Ley N.° 27972', 'LEY_27972', '2026-v1', 'Servicios públicos locales',
     'Resumen didáctico simulado: la municipalidad participa en la organización y prestación de servicios públicos locales prioritarios.', TRUE, FALSE, 'simulated'),
    ('LEY27972-06', 'Ley N.° 27972', 'LEY_27972', '2026-v1', 'Planeamiento y presupuesto',
     'Resumen didáctico simulado: la gestión municipal articula instrumentos de planeamiento, presupuesto y programación participativa.', TRUE, FALSE, 'simulated'),

    ('DL1252-01', 'D. L. N.° 1252 - Invierte.pe', 'DL_1252', '2026-v1', 'Programación multianual',
     'Resumen didáctico simulado: la programación multianual orienta la cartera de inversiones hacia el cierre de brechas prioritarias.', TRUE, FALSE, 'simulated'),
    ('DL1252-02', 'D. L. N.° 1252 - Invierte.pe', 'DL_1252', '2026-v1', 'Formulación y evaluación',
     'Resumen didáctico simulado: los proyectos pasan por actividades de formulación y evaluación para sustentar su conveniencia técnica y social.', TRUE, FALSE, 'simulated'),
    ('DL1252-03', 'D. L. N.° 1252 - Invierte.pe', 'DL_1252', '2026-v1', 'Ejecución de inversiones',
     'Resumen didáctico simulado: la ejecución comprende el desarrollo de las inversiones aprobadas conforme a la programación presupuestal.', TRUE, FALSE, 'simulated'),
    ('DL1252-04', 'D. L. N.° 1252 - Invierte.pe', 'DL_1252', '2026-v1', 'Cierre de brechas',
     'Resumen didáctico simulado: el sistema de inversiones públicas busca orientar recursos hacia brechas de infraestructura y acceso a servicios públicos.', TRUE, FALSE, 'simulated'),
    ('DL1252-05', 'D. L. N.° 1252 - Invierte.pe', 'DL_1252', '2026-v1', 'Funcionamiento y seguimiento',
     'Resumen didáctico simulado: la fase de funcionamiento asegura la operación, mantenimiento y seguimiento de los activos generados por la inversión.', TRUE, FALSE, 'simulated'),
    ('DL1252-06', 'D. L. N.° 1252 - Invierte.pe', 'DL_1252', '2026-v1', 'Órganos del sistema Invierte.pe',
     'Resumen didáctico simulado: los órganos del sistema incluyen a la OPMI, Unidades Formuladoras y Unidades Ejecutoras de Inversiones con roles delimitados.', TRUE, FALSE, 'simulated'),

    ('LEY32069-01', 'Ley N.° 32069', 'LEY_32069', '2026-v1', 'Principios de contratación pública',
     'Resumen didáctico simulado: la contratación pública se rige por principios de valor por dinero, integridad, transparencia y competencia.', TRUE, FALSE, 'simulated'),
    ('LEY32069-02', 'Ley N.° 32069', 'LEY_32069', '2026-v1', 'Actuaciones preparatorias y requerimiento',
     'Resumen didáctico simulado: las actuaciones preparatorias exigen la formulación adecuada del requerimiento y estudio de mercado.', TRUE, FALSE, 'simulated'),
    ('LEY32069-03', 'Ley N.° 32069', 'LEY_32069', '2026-v1', 'Métodos de contratación y selección',
     'Resumen didáctico simulado: la selección de proveedores debe realizarse mediante procedimientos competitivos y no discriminatorios.', TRUE, FALSE, 'simulated'),
    ('LEY32069-04', 'Ley N.° 32069', 'LEY_32069', '2026-v1', 'Ejecución contractual y modificaciones',
     'Resumen didáctico simulado: las modificaciones contractuales y adicionales deben estar debidamente justificadas y dentro de los límites legales.', TRUE, FALSE, 'simulated'),
    ('LEY32069-05', 'Ley N.° 32069', 'LEY_32069', '2026-v1', 'Solución de controversias y arbitraje',
     'Resumen didáctico simulado: las controversias durante la ejecución contractual pueden resolverse mediante conciliación, junta de resolución de disputas o arbitraje.', TRUE, FALSE, 'simulated'),
    ('LEY32069-06', 'Ley N.° 32069', 'LEY_32069', '2026-v1', 'Transparencia y trazabilidad',
     'Resumen didáctico simulado: todos los actos del proceso de contratación deben ser registrados de manera pública y trazable en el sistema correspondiente.', TRUE, FALSE, 'simulated'),

    ('PDUPDM-01', 'PDU/PDM Huancayo-El Tambo', 'PDU_EL_TAMBO', '2026-v1', 'Zonificación urbana',
     'Resumen didáctico simulado: la zonificación clasifica áreas del territorio y orienta los usos permitidos, condicionados o restringidos en cada zona.', TRUE, FALSE, 'simulated'),
    ('PDUPDM-02', 'PDU/PDM Huancayo-El Tambo', 'PDU_EL_TAMBO', '2026-v1', 'Compatibilidad de uso de suelo',
     'Resumen didáctico simulado: si el uso propuesto para un proyecto es incompatible con la zonificación vigente, el expediente requiere observación y revisión jurídica.', TRUE, TRUE, 'simulated'),
    ('PDUPDM-03', 'PDU/PDM Huancayo-El Tambo', 'PDU_EL_TAMBO', '2026-v1', 'Equipamiento urbano y aportes',
     'Resumen didáctico simulado: los proyectos de habilitación y equipamiento deben prever aportes reglamentarios para recreación y servicios comunales.', TRUE, FALSE, 'simulated'),
    ('PDUPDM-04', 'PDU/PDM Huancayo-El Tambo', 'PDU_EL_TAMBO', '2026-v1', 'Zonas de riesgo',
     'Resumen didáctico simulado: una propuesta ubicada en un área identificada como riesgo alto o no mitigable debe ser observada y sometida a revisión antes de continuar.', TRUE, TRUE, 'simulated'),
    ('PDUPDM-05', 'PDU/PDM Huancayo-El Tambo', 'PDU_EL_TAMBO', '2026-v1', 'Sistema vial y movilidad urbana',
     'Resumen didáctico simulado: la red vial clasifica vías primarias, secundarias y locales, determinando secciones y servidumbres obligatorias.', TRUE, FALSE, 'simulated'),
    ('PDUPDM-06', 'PDU/PDM Huancayo-El Tambo', 'PDU_EL_TAMBO', '2026-v1', 'Desarrollo urbano sostenible y espacio público',
     'Resumen didáctico simulado: los planes promueven la protección de áreas verdes, suelo permeable y consolidación ordenada del espacio público.', TRUE, FALSE, 'simulated')
ON CONFLICT (id) DO NOTHING;
