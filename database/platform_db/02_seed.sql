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
    ('a0000000-0000-4000-a000-00000000000b', 'PRY-B', '10000000-0000-4000-a000-000000000002', 'ready'),
    ('a0000000-0000-4000-a000-00000000000c', 'PRY-C', '10000000-0000-4000-a000-000000000002', 'ready'),
    ('a0000000-0000-4000-a000-00000000000d', 'PRY-D', '10000000-0000-4000-a000-000000000002', 'ready')
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
     '10000000-0000-4000-a000-000000000002'),
    ('b0000000-0000-4000-a000-00000000000c', 'a0000000-0000-4000-a000-00000000000c', 1,
     'Proyecto C - Taller de maestranza y depósito municipal (prueba)', 'Dato ficticio para el PMV 2 (HU1.6)',
     'CASO SIMULADO - Faja marginal del Río Shullcas - El Tambo', 'taller / maestranza', 'simulated', 350000.00, 1200,
     '10000000-0000-4000-a000-000000000002'),
    ('b0000000-0000-4000-a000-00000000000d', 'a0000000-0000-4000-a000-00000000000d', 1,
     'Proyecto D - Pavimentación y ampliación vial en Av. Ferrocarril (prueba)', 'Dato ficticio para el PMV 2 (HU1.7)',
     'CASO SIMULADO - Av. Ferrocarril tramo El Tambo', 'vial / transporte', 'simulated', 480000.00, 1800,
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
-- HU2.1 / RF03 / RF12 · Corpus normativo con texto legal real (fuentes publicas oficiales)
-- 24 fragmentos normativos para El Tambo, Huancayo
-- 6 por cada grupo normativo: Ley 27972, DL 1252, Ley 32069, PDU/PDM
-- PDUPDM-02 y PDUPDM-04 marcados con has_alert=TRUE (causales de alerta)
-- Fuentes: leyes.congreso.gob.pe, busquedas.elperuano.pe, spij.minjus.gob.pe
-- =========================================================
INSERT INTO normative_documents (id, document_name, short_code, version, topic, content, in_force, has_alert, data_origin) VALUES
    ('LEY27972-01', 'Ley N.° 27972 - Ley Orgánica de Municipalidades', 'LEY_27972', '2003-v1', 'Competencias municipales (Art. 73)',
     'Art. 73.- Materias de competencia municipal. Las funciones específicas municipales que se derivan de las competencias se ejercen con carácter exclusivo o compartido entre las municipalidades provinciales y distritales. El rol de las municipalidades provinciales comprende: a) Planificar integralmente el desarrollo local y el ordenamiento territorial, en el nivel provincial. b) Promover la coordinación estratégica de los planes integrales de desarrollo distrital. c) Emitir las normas técnicas generales en materia de organización del espacio físico y uso del suelo. Fuente: leyes.congreso.gob.pe/Documentos/Leyes/27972.pdf', TRUE, FALSE, 'public'),
    ('LEY27972-02', 'Ley N.° 27972 - Ley Orgánica de Municipalidades', 'LEY_27972', '2003-v1', 'Organización del espacio físico y uso del suelo (Art. 79)',
     'Art. 79.- Organización del espacio físico y uso del suelo. Funciones exclusivas de municipalidades provinciales: 1.1 Aprobar el Plan de Acondicionamiento Territorial que identifique áreas urbanas, de expansión urbana, de protección o seguridad por riesgos naturales, áreas agrícolas y de conservación ambiental. 1.2 Aprobar el Plan de Desarrollo Urbano, el Plan de Desarrollo Rural, el Esquema de Zonificación de áreas urbanas y demás planes específicos. Funciones exclusivas distritales: 3.3 Normar, regular y otorgar autorizaciones, derechos y licencias para habilitaciones urbanas, construcción, remodelación o demolición de inmuebles, y apertura de establecimientos conforme a la zonificación. Fuente: leyes.congreso.gob.pe/Documentos/Leyes/27972.pdf', TRUE, FALSE, 'public'),
    ('LEY27972-03', 'Ley N.° 27972 - Ley Orgánica de Municipalidades', 'LEY_27972', '2003-v1', 'Concejo municipal - funciones normativas y fiscalizadoras (Arts. 5 y 9)',
     'Art. 5.- El concejo municipal, provincial y distrital, está conformado por el alcalde y el número de regidores que establezca el JNE. El concejo municipal ejerce funciones normativas y fiscalizadoras. Art. 9.- Atribuciones del concejo municipal: 1) Aprobar los Planes de Desarrollo Municipal Concertados y el Presupuesto Participativo. 5) Aprobar el Plan de Desarrollo Urbano, el Esquema de Zonificación. 8) Aprobar, modificar o derogar las ordenanzas y dejar sin efecto los acuerdos. 22) Fiscalizar la gestión pública de la municipalidad. Fuente: leyes.congreso.gob.pe/Documentos/Leyes/27972.pdf', TRUE, FALSE, 'public'),
    ('LEY27972-04', 'Ley N.° 27972 - Ley Orgánica de Municipalidades', 'LEY_27972', '2003-v1', 'Alcaldía - funciones ejecutivas (Arts. 6 y 20)',
     'Art. 6.- La alcaldía es el órgano ejecutivo del gobierno local. El alcalde es el representante legal de la municipalidad y su máxima autoridad administrativa. Art. 20.- Son atribuciones del alcalde: 1) Defender y cautelar los derechos e intereses de la municipalidad y los vecinos. 3) Ejecutar los acuerdos del concejo municipal, bajo responsabilidad. 6) Dictar decretos y resoluciones de alcaldía, con sujeción a las leyes y ordenanzas. 7) Dirigir la ejecución de los planes de desarrollo municipal. 29) Administrar los recursos económicos y financieros, de acuerdo con la ley y el presupuesto aprobado. Fuente: leyes.congreso.gob.pe/Documentos/Leyes/27972.pdf', TRUE, FALSE, 'public'),
    ('LEY27972-05', 'Ley N.° 27972 - Ley Orgánica de Municipalidades', 'LEY_27972', '2003-v1', 'Servicios públicos locales (Arts. IV TP, 73.2 y 80)',
     'Art. IV TP.- Los gobiernos locales representan al vecindario, promueven la adecuada prestación de los servicios públicos locales y el desarrollo integral, sostenible y armónico de su circunscripción. Art. 73.2.- Servicios públicos locales: saneamiento ambiental, salubridad y salud; tránsito, circulación y transporte público; educación, cultura, deporte y recreación; seguridad ciudadana; abastecimiento y comercialización. Art. 80.- Municipalidades distritales: proveer limpieza pública, regular aseo e higiene en establecimientos comerciales, industriales y viviendas, instalar y mantener servicios higiénicos públicos. Fuente: leyes.congreso.gob.pe/Documentos/Leyes/27972.pdf', TRUE, FALSE, 'public'),
    ('LEY27972-06', 'Ley N.° 27972 - Ley Orgánica de Municipalidades', 'LEY_27972', '2003-v1', 'Planeamiento y presupuesto participativo (Arts. IX TP, 53 y 97)',
     'Art. IX TP.- El proceso de planeación local es integral, permanente y participativo, articulando a las municipalidades con sus vecinos. Art. 53.- Las municipalidades se rigen por presupuestos participativos anuales como instrumentos de administración y gestión, los cuales se formulan, aprueban y ejecutan conforme a la ley de la materia, y en concordancia con los planes de desarrollo concertados de su jurisdicción. El presupuesto municipal debe sustentarse en el equilibrio real de sus ingresos y egresos. Art. 97.- El Consejo de Coordinación Local Provincial procede a coordinar, concertar y proponer el Plan de Desarrollo Municipal Provincial Concertado. Fuente: leyes.congreso.gob.pe/Documentos/Leyes/27972.pdf', TRUE, FALSE, 'public'),

    ('DL1252-01', 'D. L. N.° 1252 - Invierte.pe (TUO D.S. 242-2018-EF)', 'DL_1252', '2018-TUO', 'Programación multianual de inversiones (Art. 4.1.a)',
     'Art. 4.1.a) Programación Multianual de Inversiones: Consiste en un proceso de coordinación y articulación interinstitucional e intergubernamental, de proyección trianual, como mínimo, tomando en cuenta los fondos públicos destinados a la inversión proyectados en el Marco Macroeconómico Multianual. Dicha programación debe vincular los objetivos nacionales, regionales y locales establecidos en el planeamiento estratégico con la priorización y asignación multianual de fondos públicos, y orientarse al cierre de brechas de infraestructura o de acceso a servicios públicos para la población. Fuente: busquedas.elperuano.pe - D.S. 242-2018-EF', TRUE, FALSE, 'public'),
    ('DL1252-02', 'D. L. N.° 1252 - Invierte.pe (TUO D.S. 242-2018-EF)', 'DL_1252', '2018-TUO', 'Formulación y evaluación de proyectos (Art. 4.1.b)',
     'Art. 4.1.b) Formulación y Evaluación: Comprende la formulación del proyecto, de aquellas propuestas de inversión necesarias para alcanzar las metas establecidas en la programación multianual, y la evaluación sobre la pertinencia de su ejecución, debiendo considerarse los recursos para la operación y mantenimiento del proyecto y las formas de financiamiento. La formulación se realiza a través de una ficha técnica y solo en el caso de proyectos de alta complejidad se requiere el nivel de estudio que sustente la concepción técnica y el dimensionamiento. Los proyectos deben encontrarse registrados en el Banco de Inversiones. Fuente: busquedas.elperuano.pe - D.S. 242-2018-EF', TRUE, FALSE, 'public'),
    ('DL1252-03', 'D. L. N.° 1252 - Invierte.pe (TUO D.S. 242-2018-EF)', 'DL_1252', '2018-TUO', 'Ejecución de inversiones (Art. 4.1.c y 4.3)',
     'Art. 4.1.c) Ejecución: Comprende la elaboración del expediente técnico o documento equivalente y la ejecución física y financiera respectiva. Art. 4.3.- Únicamente pueden asignarse fondos públicos e iniciarse la fase de Ejecución de aquellas inversiones que están registradas en el Banco de Inversiones y cuenten con la declaración de viabilidad, cuando corresponda. Fuente: busquedas.elperuano.pe - D.L. 1252', TRUE, FALSE, 'public'),
    ('DL1252-04', 'D. L. N.° 1252 - Invierte.pe (TUO D.S. 242-2018-EF)', 'DL_1252', '2018-TUO', 'Cierre de brechas de infraestructura (Arts. 1 y 3.a)',
     'Art. 1.- Objeto: Créase el Sistema Nacional de Programación Multianual y Gestión de Inversiones con la finalidad de orientar el uso de los recursos públicos destinados a la inversión para la efectiva prestación de servicios y la provisión de la infraestructura necesaria para el desarrollo del país. Art. 3.a) La programación multianual de la inversión debe ser realizada considerando como principal objetivo el cierre de brechas de infraestructura o de acceso a servicios públicos para la población. Art. 3.d) Los recursos destinados a la inversión deben procurar el mayor impacto en la sociedad. Fuente: leyes.congreso.gob.pe/Documentos/DecretosLegislativos/01252.pdf', TRUE, FALSE, 'public'),
    ('DL1252-05', 'D. L. N.° 1252 - Invierte.pe (TUO D.S. 242-2018-EF)', 'DL_1252', '2018-TUO', 'Funcionamiento y seguimiento (Arts. 4.1.d, 5.2 y 8)',
     'Art. 4.1.d) Funcionamiento: Comprende la operación y mantenimiento de los activos generados con la ejecución de la inversión pública y la provisión de los servicios implementados con dicha inversión. En esta fase las inversiones pueden ser objeto de evaluaciones ex post con el fin de obtener lecciones aprendidas que permitan mejoras en futuras inversiones, así como la rendición de cuentas. Art. 5.2.- El MEF gestiona los mecanismos para el seguimiento y monitoreo a través del Sistema de Seguimiento de Inversiones y el Banco de Inversiones. Art. 8.- Proceso de Seguimiento y Evaluación de las inversiones. Fuente: busquedas.elperuano.pe - D.S. 242-2018-EF', TRUE, FALSE, 'public'),
    ('DL1252-06', 'D. L. N.° 1252 - Invierte.pe (TUO D.S. 242-2018-EF)', 'DL_1252', '2018-TUO', 'Órganos del sistema Invierte.pe: OPMI, UF, UEI (Art. 5)',
     'Art. 5.1.- Son órganos del Sistema: la DGPMI del MEF, los Órganos Resolutivos, las OPMI, las Unidades Formuladoras y las Unidades Ejecutoras de Inversiones. Art. 5.4.- Las OPMI son responsables de la fase de Programación Multianual, verifican el enmarcamiento de la inversión, y realizan el seguimiento de metas e indicadores. Art. 5.5.- Las UF son responsables de la fase de Formulación y Evaluación; aplican metodologías, parámetros y normas técnicas; elaboran fichas técnicas y estudios de preinversión; y declaran la viabilidad. Art. 5.7.- Las UEI son responsables de la ejecución y se sujetan al diseño aprobado en el Banco de Inversiones. Fuente: leyes.congreso.gob.pe/Documentos/DecretosLegislativos/01252.pdf', TRUE, FALSE, 'public'),

    ('LEY32069-01', 'Ley N.° 32069 - Ley General de Contrataciones Públicas', 'LEY_32069', '2024-v1', 'Principios de contratación pública (Art. 5)',
     'Art. 5.1.- Las contrataciones públicas se rigen bajo los siguientes principios: c) Valor por dinero: Las entidades contratantes maximizan el valor de lo que obtienen, en términos de eficiencia, eficacia y economía, considerando calidad, sostenibilidad y evaluación de costos y plazos, no procurando únicamente el menor precio. d) Integridad: Conducta obligada de todo participante, guiado por honestidad, veracidad y rendición de cuentas, que evita y denuncia prácticas indebidas o corruptas. i) Transparencia y facilidad de uso: Las actuaciones y decisiones se basan en reglas y criterios claros y accesibles; las entidades garantizan el acceso público y oportuno a la información del proceso. Fuente: El Peruano, 24/06/2024 - spij.minjus.gob.pe', TRUE, FALSE, 'public'),
    ('LEY32069-02', 'Ley N.° 32069 - Ley General de Contrataciones Públicas', 'LEY_32069', '2024-v1', 'Actuaciones preparatorias y requerimiento (Art. 46)',
     'Art. 46.1.- El requerimiento da inicio al proceso de contratación, en el marco de la PMBSO y las etapas presupuestarias, considerando el principio de valor por dinero. El área usuaria determina el requerimiento en coordinación con la dependencia encargada de contrataciones, identificando la finalidad pública y los objetivos de la contratación. Art. 46.2.- Las entidades gestionan las contrataciones considerando todo el ciclo de vida de los bienes, servicios y obras. Art. 46.3.- El requerimiento permite el acceso de los proveedores en condiciones de igualdad, sin obstaculizar la competencia ni direccionar el proceso. Fuente: El Peruano, 24/06/2024 - spij.minjus.gob.pe', TRUE, FALSE, 'public'),
    ('LEY32069-03', 'Ley N.° 32069 - Ley General de Contrataciones Públicas', 'LEY_32069', '2024-v1', 'Métodos de contratación y selección (Arts. 53 y 54)',
     'Art. 54.1.- Son procedimientos de selección competitivos: a) La licitación pública, para bienes y obras. b) El concurso público, para servicios. Art. 54.2.- El reglamento establece modalidades abreviadas y diferenciadas (subasta inversa electrónica, comparación de precios, compra pública de innovación). Art. 54.3.- Las entidades realizan procedimientos de selección competitivos, salvo excepciones previstas en la ley, asegurando que la adjudicación recaiga en la oferta más conveniente bajo el principio de valor por dinero. Art. 34.- Contratos menores ≤ 8 UIT. Fuente: El Peruano, 24/06/2024 - spij.minjus.gob.pe', TRUE, FALSE, 'public'),
    ('LEY32069-04', 'Ley N.° 32069 - Ley General de Contrataciones Públicas', 'LEY_32069', '2024-v1', 'Ejecución contractual y modificaciones (Arts. 63 y 64)',
     'Art. 63.1.- El contrato puede ser modificado por acuerdo entre las partes, por disposición de la entidad o a solicitud del contratista, para alcanzar la finalidad del contrato de manera oportuna y eficiente. Art. 63.2.- Las modificaciones no deben afectar el equilibrio económico-financiero del contrato. Art. 63.3.- Supuestos: a) Prestaciones adicionales, b) Reducción de prestaciones, c) Ampliaciones de plazo, d) Hechos sobrevinientes no imputables a las partes. Art. 64.- Prestaciones adicionales: hasta 25% del contrato original en bienes/servicios; en obras, hasta 15% por la autoridad administrativa y hasta 50% con aprobación del Titular o la Contraloría. Fuente: El Peruano, 24/06/2024 - spij.minjus.gob.pe', TRUE, FALSE, 'public'),
    ('LEY32069-05', 'Ley N.° 32069 - Ley General de Contrataciones Públicas', 'LEY_32069', '2024-v1', 'Solución de controversias y arbitraje (Arts. 76 y 84)',
     'Art. 76.1.- Las controversias sobre ejecución, interpretación, resolución, inexistencia, ineficacia o nulidad del contrato se resuelven mediante: a) Junta de Prevención y Resolución de Disputas (JPRD), b) Conciliación, c) Arbitraje, d) Otros mecanismos de contratos estandarizados internacionales. Art. 84.- El arbitraje es de derecho; puede ser institucional o ad hoc (solo si ≤ 10 UIT). El laudo es definitivo, inapelable y de obligatorio cumplimiento desde su notificación a través de PLADICOP. Los árbitros deben integrar nóminas registradas ante el OECE. Fuente: El Peruano, 24/06/2024 - spij.minjus.gob.pe', TRUE, FALSE, 'public'),
    ('LEY32069-06', 'Ley N.° 32069 - Ley General de Contrataciones Públicas', 'LEY_32069', '2024-v1', 'Transparencia y trazabilidad - PLADICOP (Art. 41)',
     'Art. 41.1.- La Plataforma Digital para las Contrataciones Públicas (PLADICOP) integra los sistemas que garantizan el acceso y disponibilidad de información sobre contrataciones públicas, incluyendo régimen general, regímenes especiales y contratos menores. Art. 41.2.- Las entidades contratantes tienen la obligación de registrar toda la información de las fases de contratación, garantizando transparencia, trazabilidad, acceso público y fiscalización en tiempo real. Art. 41.4.- Los actos publicados en PLADICOP gozan de plena validez jurídica y eficacia, surtiendo efectos de notificación formal. Fuente: El Peruano, 24/06/2024 - spij.minjus.gob.pe', TRUE, FALSE, 'public'),

    ('PDUPDM-01', 'PDM Huancayo 2017-2037 (O.M. N.° 636-2020-MPH/CM)', 'PDU_EL_TAMBO', '2020-OM636', 'Zonificación urbana (Título III del Reglamento de Zonificación)',
     'PDM Huancayo 2017-2037, Título III: Zonificación Urbana y Parámetros Urbanísticos. Clasifica el suelo en zonas: Residencial Densidad Media (RDM) predominante en El Tambo, Residencial Densidad Alta (RDA) sobre ejes viales como Av. Mariscal Castilla, Comercio Zonal (CZ) en corredores como Av. Huancavelica y Calle Real, Industria Elemental (I-1), Equipamiento de Educación (E-1 a E-3 incluyendo UNCP) y Salud (H-1 a H-4 incluyendo Hospital EsSalud), y Zonas de Recreación Pública (ZRP) intangibles para edificación privada. Norma complementaria: D.S. N.° 012-2022-VIVIENDA, Arts. 30 al 42. Fuente: munihuancayo.gob.pe - O.M. N.° 636-2020-MPH/CM', TRUE, FALSE, 'public'),
    ('PDUPDM-02', 'PDM Huancayo 2017-2037 (O.M. N.° 636-2020-MPH/CM)', 'PDU_EL_TAMBO', '2020-OM636', 'Compatibilidad de uso de suelo (Índice de Usos y Cuadro de Compatibilidad)',
     'PDM Huancayo 2017-2037: Si el uso propuesto es catalogado como No Conforme o Incompatible según el Índice de Usos para la zona, la Gerencia de Desarrollo Urbano emite resolución denegatoria obligatoria. Para usos preexistentes no conformes: se prohíben ampliaciones, solo se permiten obras de conservación y seguridad, y en caso de siniestro >50% caduca el derecho. La vía excepcional de cambio de zonificación requiere sustento vial, consulta vecinal de 30 días y aprobación del Concejo por Ordenanza. El ejercicio de uso incompatible sin autorización acarrea clausura definitiva, paralización de obra y multas (RASA). Norma complementaria: Ley N.° 28976, Arts. 7-8 y D.S. N.° 012-2022-VIVIENDA, Arts. 120-124. Fuente: munihuancayo.gob.pe', TRUE, TRUE, 'public'),
    ('PDUPDM-03', 'PDM Huancayo 2017-2037 (O.M. N.° 636-2020-MPH/CM)', 'PDU_EL_TAMBO', '2020-OM636', 'Equipamiento urbano y aportes reglamentarios (RNE TH.010, Arts. 10-14)',
     'PDM Huancayo 2017-2037: En habilitaciones urbanas en El Tambo el titular cede gratuitamente: Recreación Pública (ZRP) 8-13% del área habilitable (frente a vías, pendientes ≤15%), Educación (MINEDU) 2-3%, Parques Zonales 1-2% (MPH) y Otros Fines 1-2% (equipamiento cívico/seguridad). Cuando el aporte resulte menor al área mínima funcional, la normativa autoriza redención en dinero a favor del fondo municipal de equipamiento urbano, calculada sobre el valor arancelario o comercial del predio. Norma complementaria: RNE TH.010, Cap. II, Arts. 10-14 y GH.020, Arts. 18-25. Fuente: munihuancayo.gob.pe - gob.pe/vivienda', TRUE, FALSE, 'public'),
    ('PDUPDM-04', 'PDM Huancayo 2017-2037 (O.M. N.° 636-2020-MPH/CM)', 'PDU_EL_TAMBO', '2020-OM636', 'Zonas de riesgo alto o no mitigable (SINAGERD - Ley 29664)',
     'PDM Huancayo 2017-2037: Las zonas no mitigables son intangibles e inhabitables; se prohíbe la emisión de licencias de edificación, habilitaciones urbanas, constancias de posesión y dotación de redes de servicios definitivos. Sectores críticos en El Tambo: faja marginal del Río Mantaro (riesgo hidrológico), faja marginal del Río Shullcas (desbordes y huaycos), Río Florido y Río Seco (inundaciones pluviales), Canal CIMIRM (desbordes y contaminación), cerros orientales y quebradas (deslizamientos y movimientos en masa). Las terrazas centrales consolidadas poseen mejor capacidad portante y menor riesgo sísmico. Norma complementaria: Ley N.° 29664, Ley N.° 30556 y CENEPRED-SIGRID. Fuente: sigrid.cenepred.gob.pe - munieltambo.gob.pe', TRUE, TRUE, 'public'),
    ('PDUPDM-05', 'PDM Huancayo 2017-2037 (O.M. N.° 636-2020-MPH/CM)', 'PDU_EL_TAMBO', '2020-OM636', 'Sistema vial y movilidad urbana (Reglamento del Sistema Vial Metropolitano)',
     'PDM Huancayo 2017-2037, Reglamento del Sistema Vial Metropolitano: Clasifica las vías en Expresas (tránsito ininterrumpido con control de accesos, incluyendo Vía de Evitamiento y Autovía del Mantaro), Arteriales (Av. Mariscal Castilla como eje principal, Av. Ferrocarril y Av. Huancavelica), Colectoras (Av. Evitamiento, Av. Mariátegui, Av. Calmell del Solar, Av. Tahuantinsuyo) y Locales (calles residenciales con máx. 30 km/h y veredas mínimo 1.20 m). Toda obra o habilitación nueva debe respetar los retiros de alineamiento vial del Plano de Vías para garantizar el derecho de vía y futuras ampliaciones de calzadas y ciclovías. Norma complementaria: RNE GH.020. Fuente: munihuancayo.gob.pe', TRUE, FALSE, 'public'),
    ('PDUPDM-06', 'PDM Huancayo 2017-2037 (O.M. N.° 636-2020-MPH/CM)', 'PDU_EL_TAMBO', '2020-OM636', 'Desarrollo urbano sostenible y espacio público (Ley DUS 31313)',
     'PDM Huancayo 2017-2037: Los parques, plazas, alamedas y riberas protegidas son bienes de dominio público inalienables, imprescriptibles e inembargables; se prohíbe el cambio de uso de áreas verdes a fines habitacionales o comerciales privados. Ejes ecológicos: recuperación ambiental e intangibilidad de riberas del Shullcas y Mantaro para malecones ecológicos. Huancayo y El Tambo registran un índice de áreas verdes per cápita inferior a 4 m²/hab (frente a 9 m²/hab recomendados por la OMS). El PDM obliga a articular los aportes de recreación y parques zonales para conformar una red conectada de espacios públicos arborizados. Norma complementaria: Ley N.° 31313, D.S. N.° 012-2022-VIVIENDA, Ley N.° 31199 y D.S. N.° 001-2023-VIVIENDA. Fuente: munihuancayo.gob.pe - gob.pe/vivienda', TRUE, FALSE, 'public'),
    ('LEY26850-HIST', 'Ley N.° 26850 - Ley de Contrataciones y Adquisiciones del Estado (Sustituida)', 'LEY_26850', '1997-derogada', 'Contrataciones públicas históricas (Art. 1 - Sustituida por Ley 30225)',
     'Art. 1.- Objeto y ámbito de aplicación histórico. Disposición histórica sustituida y derogada expresamente por la Ley de Contrataciones vigente. Se conserva en el repositorio únicamente como antecedente normativo y referencia histórica; no aplica para contrataciones ni obras públicas nuevas.', FALSE, FALSE, 'public')
ON CONFLICT (id) DO UPDATE SET
    document_name = EXCLUDED.document_name,
    version = EXCLUDED.version,
    topic = EXCLUDED.topic,
    content = EXCLUDED.content,
    data_origin = EXCLUDED.data_origin;

-- =========================================================
-- Semillas de datos territoriales de accesibilidad social (HU1.4)
-- Conjunto explícitamente simulado para el distrito de El Tambo.
-- PRY-A: Caso completo con las tres categorías disponibles.
-- PRY-B: Caso incompleto con categorías faltantes ('Información insuficiente').
-- =========================================================
INSERT INTO territorial_social_indicators
    (id, project_id, project_code, category, indicator_name, metric_value, metric_unit, has_sufficient_data, source_name, data_origin, description)
VALUES
    -- PRY-A (Caso completo: Salud, Educación, Transporte)
    ('71000000-0000-4000-a000-000000000001', 'a0000000-0000-4000-a000-00000000000a', 'PRY-A', 'salud',
     'Distancia peatonal al establecimiento de salud de primer nivel (I-1/I-2)', 450.00, 'metros', TRUE,
     'Dataset territorial simulado SIPRIM El Tambo - RENAES MINSA (Simulado)', 'simulated',
     'Puesto de Salud El Tambo I a 450 metros a pie. Cobertura peatonal adecuada.'),

    ('71000000-0000-4000-a000-000000000002', 'a0000000-0000-4000-a000-00000000000a', 'PRY-A', 'educacion',
     'Distancia a la institución educativa pública inicial/primaria más cercana', 320.00, 'metros', TRUE,
     'Dataset territorial simulado SIPRIM El Tambo - Censo Educativo MINEDU (Simulado)', 'simulated',
     'I.E. Primaria N.° 30154 a 320 metros. Ubicada dentro del radio óptimo de 500 m.'),

    ('71000000-0000-4000-a000-000000000003', 'a0000000-0000-4000-a000-00000000000a', 'PRY-A', 'transporte',
     'Tiempo de caminata al paradero o eje de transporte público más cercano', 6.00, 'minutos', TRUE,
     'Dataset territorial simulado SIPRIM El Tambo - Sistema Vial Metropolitano MPH (Simulado)', 'simulated',
     'Paradero Av. Mariscal Castilla a 6 minutos a pie (420 metros). Servicio continuo.'),

    -- PRY-B (Caso incompleto: Salud con dato; Educación y Transporte sin información suficiente)
    ('71000000-0000-4000-a000-000000000004', 'a0000000-0000-4000-a000-00000000000b', 'PRY-B', 'salud',
     'Distancia peatonal al establecimiento de salud de primer nivel (I-1/I-2)', 680.00, 'metros', TRUE,
     'Dataset territorial simulado SIPRIM El Tambo - RENAES MINSA (Simulado)', 'simulated',
     'Centro de Salud El Tambo a 680 metros. Supera el radio peatonal ideal de 500 metros.'),

    ('71000000-0000-4000-a000-000000000005', 'a0000000-0000-4000-a000-00000000000b', 'PRY-B', 'educacion',
     'Distancia a la institución educativa pública inicial/primaria más cercana', NULL, NULL, FALSE,
     'Dataset territorial simulado SIPRIM El Tambo (Sin cobertura de padrón escolar en la zona)', 'simulated',
     'Información insuficiente'),

    ('71000000-0000-4000-a000-000000000006', 'a0000000-0000-4000-a000-00000000000b', 'PRY-B', 'transporte',
     'Tiempo de caminata al paradero o eje de transporte público más cercano', NULL, NULL, FALSE,
     'Dataset territorial simulado SIPRIM El Tambo (Sin cobertura de rutas autorizadas registrada)', 'simulated',
     'Información insuficiente')
ON CONFLICT (id) DO UPDATE SET
    indicator_name = EXCLUDED.indicator_name,
    metric_value = EXCLUDED.metric_value,
    metric_unit = EXCLUDED.metric_unit,
    has_sufficient_data = EXCLUDED.has_sufficient_data,
    source_name = EXCLUDED.source_name,
    data_origin = EXCLUDED.data_origin,
    description = EXCLUDED.description;

-- =========================================================
-- Semillas de datos ambientales territoriales (HU1.6)
-- Conjunto explícitamente simulado para el distrito de El Tambo.
-- PRY-A: Caso con impacto moderado/bajo mitigable y sustento verificable.
-- PRY-C: Caso con riesgo alto relevante por cercanía a faja marginal fluvial.
-- PRY-B: Caso con información insuficiente (falta de DIA y línea base).
-- =========================================================
INSERT INTO project_environmental_records
    (id, project_id, project_code, has_sufficient_data, environmental_component,
     declared_impacts, declared_measures, verifiable_evidence, proximity_to_water_meters,
     is_in_protected_or_risk_area, source_name, data_origin, description)
VALUES
    -- PRY-A (Impacto moderado/bajo con sustento y mitigaciones)
    ('81000000-0000-4000-a000-000000000001', 'a0000000-0000-4000-a000-00000000000a', 'PRY-A', TRUE,
     'aire_acustico_residuos',
     'El expediente declara generación temporal de polvo, ruido diurno durante obras preliminares y demolición de pavimento deteriorado.',
     'Aspersión de agua diaria para control de material particulado, cerco perimétrico con malla antipolvo y horario de trabajo restringido de 08:00 a 17:00 h.',
     'Ubicación en trama urbana consolidada de El Tambo. Distancia superior a 400 m de fajas marginales o cursos hídricos; fuera de áreas naturales protegidas o de conservación (PDM Huancayo / CENEPRED-SIGRID).',
     420.00, FALSE,
     'Dataset ambiental simulado SIPRIM El Tambo - PDM Huancayo / CENEPRED (Simulado)', 'simulated',
     'Losa deportiva en área consolidada. Impactos menores y mitigables mediante buenas prácticas de obra civil.'),

    -- PRY-C (Riesgo ambiental ALTO: Faja marginal del Río Shullcas)
    ('81000000-0000-4000-a000-000000000002', 'a0000000-0000-4000-a000-00000000000c', 'PRY-C', TRUE,
     'recurso_hidrico_ecosistema',
     'El administrado declara almacenamiento temporal de vehículos y depósito de materiales sin vertimientos contaminantes a la quebrada.',
     'Piso de afirmado compacto y cuneta perimétrica rústica sin trampa de grasas ni canalización certificada.',
     'Predio emplazado a 25 metros de la faja marginal del Río Shullcas. Zona clasificada como de muy alto riesgo no mitigable e intangible por el PDM Huancayo 2017-2037 (O.M. N.° 636-MPH) y Ley 29664 (SINAGERD); riesgo crítico de escorrentía con hidrocarburos y alteración del ecosistema ribereño.',
     25.00, TRUE,
     'Dataset ambiental simulado SIPRIM El Tambo - PDM Huancayo / ANA-ALA Mantaro / SIGRID (Simulado)', 'simulated',
     'Instalación de maestranza en faja marginal. Riesgo severo de contaminación fluvial y afectación hidrológica no mitigable.'),

    -- PRY-B (Información ambiental insuficiente: falta DIA y línea base)
    ('81000000-0000-4000-a000-000000000003', 'a0000000-0000-4000-a000-00000000000b', 'PRY-B', FALSE,
     'integral',
     NULL,
     NULL,
     NULL,
     NULL, NULL,
     'Catastro Municipal El Tambo (Sin Declaración de Impacto Ambiental ni línea base registrada)', 'simulated',
     'Información insuficiente'),

    -- PRY-D (Caso con afectación de áreas verdes y medidas insuficientes)
    ('81000000-0000-4000-a000-000000000004', 'a0000000-0000-4000-a000-00000000000d', 'PRY-D', TRUE,
     'aire_acustico_residuos',
     'El administrado declara obras de pavimentación con generación diurna de polvo y ruido por maquinaria pesada.',
     'Riego periódico de calzada con cisterna y desvío de tránsito vehicular por calles alternas.',
     'Eje vial metropolitano consolidado en El Tambo. Distancia superior a 350 m a cursos hídricos; fuera de fajas marginales o zonas no mitigables del PDM.',
     350.00, FALSE,
     'Dataset ambiental simulado SIPRIM El Tambo - PDM Huancayo (Simulado)', 'simulated',
     'Pavimentación en trama consolidada. Impactos generales mitigables, pero interviene berma central arborizada.')
ON CONFLICT (id) DO UPDATE SET
    declared_impacts = EXCLUDED.declared_impacts,
    declared_measures = EXCLUDED.declared_measures,
    verifiable_evidence = EXCLUDED.verifiable_evidence,
    proximity_to_water_meters = EXCLUDED.proximity_to_water_meters,
    is_in_protected_or_risk_area = EXCLUDED.is_in_protected_or_risk_area,
    source_name = EXCLUDED.source_name,
    data_origin = EXCLUDED.data_origin,
    description = EXCLUDED.description;



-- =========================================================
-- Semillas de datos de áreas verdes (HU1.7)
-- Conjunto explícitamente simulado para el distrito de El Tambo.
-- PRY-A: Conservación activa con sustento y medidas suficientes (+15 pts).
-- PRY-B: Información insuficiente (sin bonificación, puntaje sin determinar).
-- PRY-C: Riesgo alto en HU1.6 (la bonificación NO elude la compuerta humana).
-- PRY-D: Afectación de áreas verdes con medidas insuficientes (-20 pts).
-- =========================================================
INSERT INTO project_green_area_records
    (id, project_id, project_code, has_sufficient_data, total_project_area_m2, green_area_m2,
     green_area_percentage, delimitation_description, declared_affectation, verifiable_affectation,
     affectation_type, protection_measures, has_sufficient_measures, score_effect_pts, effect_type,
     calculation_explanation, source_name, data_origin, description)
VALUES
    -- PRY-A (Conservación con sustento y medidas suficientes: Bonificación +15 pts)
    ('91000000-0000-4000-a000-000000000001', 'a0000000-0000-4000-a000-00000000000a', 'PRY-A', TRUE,
     4600.00, 850.00, 18.48,
     'Polígono delimitado en plano perimétrico PL-01: sector norte y franja este del complejo deportivo El Tambo, con cerco vivo de cipreses y grass natural.',
     'El expediente prevé conservar las áreas verdes perimetrales existentes e incorporar 150 m² adicionales de cobertura vegetal.',
     'Inspección catastral municipal confirma que el proyecto respeta la zonificación recreativa ZRP del PDM y no reduce la masa vegetal existente.',
     'conservacion_positiva',
     'Instalación de cerco de protección durante obras civiles, sistema de riego por goteo y plan de arborización con especies nativas (queñua y aliso).',
     TRUE, 15.00, 'bonus',
     'Bonificación ambiental (+15.0 pts): el proyecto conserva y protege 850.00 m² (18.48% del predio) de áreas verdes con delimitación verificada y medidas de protección suficientes.',
     'Dataset territorial simulado SIPRIM El Tambo - Gerencia de Gestión Ambiental MPH (Simulado)', 'simulated',
     'Conservación de áreas verdes con incremento neto de cobertura vegetal.'),

    -- PRY-B (Información insuficiente: sin bonificación, efecto indeterminado)
    ('91000000-0000-4000-a000-000000000002', 'a0000000-0000-4000-a000-00000000000b', 'PRY-B', FALSE,
     NULL, NULL, NULL,
     NULL, NULL, NULL,
     NULL, NULL, FALSE, NULL, 'indeterminado',
     'Información insuficiente: no se dispone de superficie, delimitación ni sustento técnico de áreas verdes. Por regla de precaución (CA-HU1.7-02), no se concede ventaja ambiental ni bonificación automática.',
     'Catastro Municipal El Tambo (Sin catastro verde ni delimitación)', 'simulated',
     'Información insuficiente'),

    -- PRY-C (Riesgo ambiental alto en HU1.6: franja ribereña Río Shullcas)
    ('91000000-0000-4000-a000-000000000003', 'a0000000-0000-4000-a000-00000000000c', 'PRY-C', TRUE,
     3200.00, 400.00, 12.50,
     'Franja ribereña adyacente a faja marginal del Río Shullcas.',
     'El administrado declara conservación de vegetación ribereña.',
     'Emplazamiento en faja marginal intangible no mitigable. Aunque declara conservar 400 m², el uso de maestranza genera riesgo crítico de contaminación sobre el ecosistema ribereño.',
     'afectacion_mitigada',
     'Cuneta rústica sin impermeabilización.',
     FALSE, 0.00, 'neutro',
     'Efecto neutro / sin ventaja convalidante: el predio se encuentra en faja marginal intangible de muy alto riesgo. La condición de riesgo alto prevalece e impide una valoración favorable automática.',
     'Dataset territorial simulado SIPRIM El Tambo - SIGRID / ANA (Simulado)', 'simulated',
     'Predio ribereño en faja marginal. Conservación declarada no neutraliza el riesgo ambiental alto.'),

    -- PRY-D (Afectación de áreas verdes con medidas insuficientes: Deducción -20 pts)
    ('91000000-0000-4000-a000-000000000004', 'a0000000-0000-4000-a000-00000000000d', 'PRY-D', TRUE,
     5200.00, 320.00, 6.15,
     'Berma central Av. Ferrocarril entre cuadras 12 y 16, El Tambo.',
     'Remoción de berma con árboles para habilitar tercer carril de tránsito vehicular.',
     'Tala y pérdida neta de 320 m² de cobertura arbórea consolidada en eje vial metropolitano.',
     'afectacion_no_mitigada',
     'No presenta plan de compensación arbórea ni trasplante de especies maduras; solo propuesta verbal de maceteros ornamentales.',
     FALSE, -20.00, 'penalizacion',
     'Deducción ambiental (-20.0 pts): el proyecto genera afectación y remoción de 320.00 m² de área verde sin medidas de reposición forestal ni compensación de biomasa acreditadas.',
     'Dataset ambiental simulado SIPRIM El Tambo - Subgerencia de Áreas Verdes (Simulado)', 'simulated',
     'Tala y reducción de áreas verdes sin compensación reglamentaria.')
ON CONFLICT (id) DO UPDATE SET
    total_project_area_m2 = EXCLUDED.total_project_area_m2,
    green_area_m2 = EXCLUDED.green_area_m2,
    green_area_percentage = EXCLUDED.green_area_percentage,
    delimitation_description = EXCLUDED.delimitation_description,
    declared_affectation = EXCLUDED.declared_affectation,
    verifiable_affectation = EXCLUDED.verifiable_affectation,
    affectation_type = EXCLUDED.affectation_type,
    protection_measures = EXCLUDED.protection_measures,
    has_sufficient_measures = EXCLUDED.has_sufficient_measures,
    score_effect_pts = EXCLUDED.score_effect_pts,
    effect_type = EXCLUDED.effect_type,
    calculation_explanation = EXCLUDED.calculation_explanation,
    source_name = EXCLUDED.source_name,
    data_origin = EXCLUDED.data_origin,
    description = EXCLUDED.description;


-- =========================================================
-- Semillas de datos demográficos de equidad de género y edad (HU1.5)
-- Conjunto explícitamente simulado para el distrito de El Tambo.
-- PRY-A: Caso completo con datos fiables de género y edad (+30 pts favorables).
-- PRY-B: Caso con información insuficiente en género y edad (sin bonificación ni proporciones inferidas).
-- PRY-C: Caso mixto (género neutro 0.0 pts, edad insuficiente null).
-- PRY-D: Caso vial con medidas acreditadas (+20 pts favorables).
-- =========================================================
INSERT INTO project_demographic_equity_records
    (id, project_id, project_code, dimension, has_sufficient_data, target_group,
     aggregated_population, aggregated_percentage, equity_criterion, declared_benefit,
     verifiable_data, has_favorable_evidence, score_effect_pts, effect_type,
     effect_explanation, source_name, data_origin, description)
VALUES
    -- PRY-A (Género: Datos suficientes, efecto favorable +15 pts)
    ('92000000-0000-4000-a000-000000000001', 'a0000000-0000-4000-a000-00000000000a', 'PRY-A', 'genero', TRUE,
     'Mujeres y niñas del área de influencia directa', 2450, 51.20,
     'Priorización de equipamiento deportivo seguro con enfoque de género, vestuarios diferenciados e iluminación integral',
     'El expediente contempla iluminación perimétrica continua, vestuarios y servicios higiénicos diferenciados, y módulos para actividades recreativas infantiles y femeninas.',
     'Censo 2017 INEI en sector 04 El Tambo: 2,450 mujeres residentes (51.2% del total poblacional). El diseño arquitectónico incluye iluminación LED en senderos y visibilidad abierta eliminando puntos ciegos.',
     TRUE, 15.00, 'favorable',
     'Efecto favorable (+15.0 pts): el proyecto beneficia directamente a 2,450 mujeres y niñas (51.2% de la población del entorno) mediante infraestructura deportiva segura, vestuarios diferenciados y eliminación de puntos ciegos.',
     'Dataset territorial simulado SIPRIM El Tambo - INEI Censo 2017 / SISFOH (Simulado)', 'simulated',
     'Equidad de género: impacto positivo directo acreditado en población femenina.'),

    -- PRY-A (Edad: Datos suficientes, efecto favorable +15 pts)
    ('92000000-0000-4000-a000-000000000002', 'a0000000-0000-4000-a000-00000000000a', 'PRY-A', 'edad', TRUE,
     'Primera infancia, niñez (<12) y adultos mayores (≥65)', 1840, 38.60,
     'Acceso universal y diseño adaptado para niñez y personas adultas mayores (criterio de vulnerabilidad etaria)',
     'Senderos peatonales nivelados, rampas accesibles con pendiente ≤6%, juegos infantiles inclusivos y circuito biosaludable gerontológico.',
     'Padrón distrital El Tambo: 1,150 niños de 0 a 11 años (24.1%) y 690 adultos mayores de 65 años (14.5%) en radio de influencia directa. Planos verifican rampas y ausencia de barreras arquitectónicas.',
     TRUE, 15.00, 'favorable',
     'Efecto favorable (+15.0 pts): el proyecto atiende prioritariamente a 1,840 personas de grupos etarios vulnerables (38.6% del entorno vecinal) incorporando diseño universal, rampas accesibles y equipamiento gerontológico.',
     'Dataset territorial simulado SIPRIM El Tambo - Padrón Demográfico Municipal (Simulado)', 'simulated',
     'Equidad de edad: inclusión prioritaria de niñez y adultos mayores con diseño universal acreditado.'),

    -- PRY-B (Género: Información insuficiente, sin ventaja automática)
    ('92000000-0000-4000-a000-000000000003', 'a0000000-0000-4000-a000-00000000000b', 'PRY-B', 'genero', FALSE,
     'Población femenina vecinal', NULL, NULL,
     'Criterio de equidad de género en servicios de salud básica',
     'Mención genérica en memoria descriptiva sin estudio demográfico ni focalización de género.',
     NULL, FALSE, NULL, 'indeterminado',
     'Información insuficiente: no se dispone de datos demográficos fiables desagregados por sexo para el área del proyecto. Conforme a CA-HU1.5-02, no se infieren proporciones ni se otorga bonificación sin evidencia.',
     'Catastro Municipal El Tambo (Sin padrón desagregado por sexo)', 'simulated',
     'Información insuficiente: sin datos fiables de género.'),

    -- PRY-B (Edad: Información insuficiente, sin ventaja automática)
    ('92000000-0000-4000-a000-000000000004', 'a0000000-0000-4000-a000-00000000000b', 'PRY-B', 'edad', FALSE,
     'Grupos etarios vulnerables (niñez y adultos mayores)', NULL, NULL,
     'Criterio de equidad etaria en atención primaria',
     'Sin información etaria registrada en el expediente técnico.',
     NULL, FALSE, NULL, 'indeterminado',
     'Información insuficiente: sin datos etarios verificables en el padrón vecinal. Conforme a CA-HU1.5-02, no se infieren distribuciones por edad ni se asigna resultado favorable sin evidencia.',
     'Catastro Municipal El Tambo (Sin censo etario focalizado)', 'simulated',
     'Información insuficiente: sin datos fiables de edad.'),

    -- PRY-C (Género: Datos suficientes, efecto neutro 0.0 pts)
    ('92000000-0000-4000-a000-000000000005', 'a0000000-0000-4000-a000-00000000000c', 'PRY-C', 'genero', TRUE,
     'Población del entorno industrial Shullcas', 620, 48.50,
     'Equidad de género en zona de servicios industriales',
     'Actividad industrial sin impacto diferenciado por sexo.',
     'Zona industrial ribereña de baja densidad residencial; sin medidas afirmativas de género.',
     FALSE, 0.00, 'neutro',
     'Efecto neutro (0.0 pts): intervención sin medidas de género afirmativas ni afectación discriminatoria sobre la población femenina (48.5%).',
     'Dataset territorial simulado SIPRIM El Tambo (Simulado)', 'simulated',
     'Equidad de género neutra sin medidas afirmativas.'),

    -- PRY-C (Edad: Información insuficiente, efecto indeterminado)
    ('92000000-0000-4000-a000-000000000006', 'a0000000-0000-4000-a000-00000000000c', 'PRY-C', 'edad', FALSE,
     'Grupos etarios de la quebrada Shullcas', NULL, NULL,
     'Equidad etaria en zona periurbana',
     'Sin estudio de composición etaria.',
     NULL, FALSE, NULL, 'indeterminado',
     'Información insuficiente: sin datos etarios fiables en faja marginal. Conforme a CA-HU1.5-02, no se infieren proporciones sin evidencia.',
     'Catastro Municipal El Tambo (Sin cobertura etaria)', 'simulated',
     'Información insuficiente: sin datos de edad.'),

    -- PRY-D (Género: Datos suficientes, efecto favorable +10 pts)
    ('92000000-0000-4000-a000-000000000007', 'a0000000-0000-4000-a000-00000000000d', 'PRY-D', 'genero', TRUE,
     'Mujeres usuarias de la vía metropolitana', 3100, 52.00,
     'Seguridad peatonal y paraderos seguros con perspectiva de género',
     'Ampliación vial con paraderos iluminados y cámaras de seguridad.',
     'Padrón distrital corredor Ferrocarril: 3,100 mujeres beneficiarias directas (52.0%). Paraderos incluyen botones de pánico e iluminación focalizada.',
     TRUE, 10.00, 'favorable',
     'Efecto favorable (+10.0 pts): el proyecto contempla paraderos seguros e iluminación focalizada para 3,100 mujeres usuarias (52.0%).',
     'Dataset de transporte simulado SIPRIM El Tambo (Simulado)', 'simulated',
     'Equidad de género en seguridad vial.'),

    -- PRY-D (Edad: Datos suficientes, efecto favorable +10 pts)
    ('92000000-0000-4000-a000-000000000008', 'a0000000-0000-4000-a000-00000000000d', 'PRY-D', 'edad', TRUE,
     'Adultos mayores y escolares que cruzan el eje vial', 1750, 29.40,
     'Seguridad vial y accesibilidad para personas mayores y escolares',
     'Cruces semaforizados con pulsador sonoro y rampas en esquinas.',
     'Corredor con 3 instituciones educativas y centro del adulto mayor: 1,750 personas de edad prioritaria (29.4%). Rampas de pendiente 6% y tiempo semafórico extendido para cruce seguro.',
     TRUE, 10.00, 'favorable',
     'Efecto favorable (+10.0 pts): cruces peatonales accesibles con semáforo sonoro y tiempo extendido para 1,750 niños y adultos mayores (29.4%).',
     'Dataset de seguridad vial simulado SIPRIM El Tambo (Simulado)', 'simulated',
     'Equidad etaria en seguridad vial.')
ON CONFLICT (id) DO UPDATE SET
    dimension = EXCLUDED.dimension,
    has_sufficient_data = EXCLUDED.has_sufficient_data,
    target_group = EXCLUDED.target_group,
    aggregated_population = EXCLUDED.aggregated_population,
    aggregated_percentage = EXCLUDED.aggregated_percentage,
    equity_criterion = EXCLUDED.equity_criterion,
    declared_benefit = EXCLUDED.declared_benefit,
    verifiable_data = EXCLUDED.verifiable_data,
    has_favorable_evidence = EXCLUDED.has_favorable_evidence,
    score_effect_pts = EXCLUDED.score_effect_pts,
    effect_type = EXCLUDED.effect_type,
    effect_explanation = EXCLUDED.effect_explanation,
    source_name = EXCLUDED.source_name,
    data_origin = EXCLUDED.data_origin,
    description = EXCLUDED.description;
