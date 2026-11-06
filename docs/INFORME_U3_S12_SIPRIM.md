# FACULTAD DE INGENIERÍA
## Escuela Académico Profesional de Ingeniería de Sistemas e Informática

**ASIGNATURA:** TALLER DE PROYECTOS 1 - ISI  
**DOCENTE:** GUEVARA JIMENEZ, JORGE ALFREDO  
**UNIDAD:** III &nbsp;|&nbsp; **SEMANA:** 12  
**FECHA DE ENTREGA:** Noviembre de 2026 &nbsp;|&nbsp; **NRC:** [NRC de Asignatura]  

---

# SIPRIM
### Sistema Multiagente para la Priorización de Proyectos de Inversión Municipal empleando Machine Learning, Arquitectura Hexagonal y Procedimientos Almacenados
**Ámbito institucional:** Municipalidad Distrital de El Tambo, Huancayo, Junín

| Integrante | Rol Scrum | Rol Técnico Principal |
| :--- | :--- | :--- |
| **Carhuamaca Vasquez, Diego Ricardo** | Product Owner | Desarrollo Backend y Lógica de Negocio |
| **Chuchon Sotelo, Ernesto Marcial Constantino** | Scrum Master | Arquitectura de Software y Modelado |
| **Huachos Lopez, Madelyn** | Scrum Team | Desarrollo Frontend e Interfaces de Usuario |
| **Reinaga Cisneros, Hermiluz Deyanira** | Scrum Team | Base de Datos y Procedimientos Almacenados |
| **Sierra Leiva, Piero Martin** | Scrum Team | Integración IA / Machine Learning y APIs |

---

## RESUMEN EJECUTIVO
(Extensión: 242 palabras)

El proyecto SIPRIM tuvo como objetivo diseñar, implementar y validar un sistema de soporte a la toma de decisiones para la preevaluación y priorización multidimensional de proyectos de inversión pública en la Municipalidad Distrital de El Tambo. El sistema aborda la fragmentación y falta de trazabilidad en la revisión de expedientes municipales mediante una arquitectura hexagonal desacoplada, integrada con modelos supervisados de Machine Learning y procedimientos almacenados transaccionales en PostgreSQL. 

Durante el ciclo de desarrollo correspondiente a los Productos Mínimos Viables PMV1 y PMV2, se construyó una aplicación con frontend en React, TypeScript y Vite, y un backend estructurado en FastAPI bajo arquitectura hexagonal (puertos y adaptadores), persistiendo en tres bases lógicas relacionales: *auth_db*, *platform_db* y *economic_db*. Se entrenaron e integraron dos modelos de Machine Learning utilizando scikit-learn sobre un dataset de 1,500 iniciativas basado en el Banco de Inversiones (Invierte.pe): Caso 1 (Riesgo de Sobrecosto mediante *RandomForestClassifier*, obteniendo Accuracy de 91.73%, Precision de 87.88%, Recall de 88.55%, F1-score de 0.8821 y ROC-AUC de 0.9690) y Caso 2 (Viabilidad de Plazo y Retraso mediante *GradientBoostingClassifier*, con Accuracy de 80.00% y F1-score de 0.7999). 

Asimismo, se implementó el procedimiento almacenado transaccional `sp_registrar_evaluacion_masiva`, validando el rendimiento con una demostración de 750 transacciones ejecutadas en 12.36 ms (23,331 transacciones/segundo) con cumplimiento estricto de propiedades ACID. La suite de pruebas automatizadas alcanzó 243 pruebas aprobadas (100% de la batería pytest), logrando una solución orientativa explicable con control humano activo (*Human-in-the-Loop*).

**Palabras clave:** Machine Learning, Arquitectura Hexagonal, Inversión Pública Municipal, Invierte.pe, Procedimientos Almacenados, Priorización de Proyectos.

---

## ABSTRACT
(Word count: 228 words)

The SIPRIM project aimed to design, implement, and validate a decision-support system for the multidimensional pre-evaluation and prioritization of municipal public investment projects in the District Municipality of El Tambo, Peru. The system addresses the fragmentation, lack of traceability, and delay in reviewing municipal project files through a decoupled hexagonal architecture integrated with supervised Machine Learning models and transactional stored procedures in PostgreSQL.

During the development cycle of Minimum Viable Products MVP1 and MVP2, a full-stack solution was developed using React, TypeScript, and Vite on the client side, and FastAPI under hexagonal architecture (ports and adapters) on the server side, persisting across three logical databases (*auth_db*, *platform_db*, and *economic_db*). Two machine learning models were trained and deployed using scikit-learn on a 1,500-project dataset derived from Peru's National Public Investment System (Invierte.pe): Use Case 1 (Cost Overrun Risk using *RandomForestClassifier*, achieving 91.73% Accuracy, 87.88% Precision, 88.55% Recall, 0.8821 F1-score, and 0.9690 ROC-AUC) and Use Case 2 (Schedule Feasibility and Delay Prediction using *GradientBoostingClassifier*, achieving 80.00% Accuracy and 0.7999 F1-score). Furthermore, a PL/pgSQL transactional stored procedure was engineered to execute bulk assessments, successfully processing 750 transactions in 12.36 ms (23,331 TPS) with complete ACID integrity. The backend automated test suite reached 243 passing tests (100%), consolidating an explainable, Human-in-the-Loop municipal solution.

**Keywords:** Machine Learning, Hexagonal Architecture, Public Municipal Investment, Stored Procedures, Project Prioritization, Invierte.pe.

---

## 1. ANÁLISIS DE PROBLEMAS

### 1.1 Identificación y formulación del problema
La Municipalidad Distrital de El Tambo (provincia de Huancayo, Junín) gestiona anualmente decenas de iniciativas de inversión pública orientadas a cerrar brechas de infraestructura vial, saneamiento, educación, salud y espacios públicos. Sin embargo, el proceso tradicional de preevaluación presenta severas limitaciones estructurales:
- **Dispersión documental:** Los expedientes técnicos y perfiles de proyectos se remiten en formatos heterogéneos, requiriendo entre 4 y 6 horas de revisión manual por expediente entre las gerencias de Desarrollo Urbano, Planeamiento y Presupuesto, y Asesoría Jurídica.
- **Sobrecostos y adendas no anticipadas:** De acuerdo con reportes de la Contraloría General de la República (2024), más del 68% de las obras públicas municipales a nivel nacional experimentan sobrecostos superiores al 15% del monto contractual original, generados principalmente por deficiencias de ingeniería en los estudios definitivos.
- **Retrasos crónicos de ejecución:** El 72% de los proyectos de inversión subnacional en la región Junín exceden en más de 90 días el cronograma inicial de ejecución programado.
- **Falta de trazabilidad y discrecionalidad:** Las decisiones de priorización de cartera carecen de un motor analítico unificado y transparente que sustente objetivamente por qué un proyecto es financiado frente a otro, dificultando la rendición de cuentas ante la ciudadanía y los órganos de control.

**Formulación del problema:**
¿De qué manera un sistema basado en arquitectura hexagonal, modelos predictivos de Machine Learning y procedimientos almacenados transaccionales permite optimizar la preevaluación y priorización multidimensional de proyectos de inversión en la Municipalidad Distrital de El Tambo, reduciendo la incertidumbre en sobrecostos y plazos bajo estricta trazabilidad y control humano?

### 1.2 Objetivos del proyecto

#### Objetivo General
Desarrollar, implementar y validar un software con arquitectura hexagonal, modelos supervisados de Machine Learning y procedimientos almacenados en PostgreSQL para la preevaluación y priorización explicable de proyectos de inversión pública en la Municipalidad Distrital de El Tambo, abarcando las capacidades operativas del PMV1 y PMV2.

#### Objetivos Específicos y Métricas de Éxito

| Objetivo Específico | Problema que soluciona | Métrica de Éxito Verificable |
| :--- | :--- | :--- |
| **OE1:** Estructurar el registro digital y validación de expedientes (PMV1). | Inconsistencia de datos, fichas incompletas y ausencia de versionado de proyectos. | 100% de expedientes con código legible (EXP-…), validación atómica y rechazo de campos faltantes (HTTP 409/422). |
| **OE2:** Evaluar la dimensión económica mediante regla determinista de costo por habitante (PMV1). | Arbitrariedad en la medición de rentabilidad socioeconómica subnacional. | Cálculo reproducible con función continua S ∈ [0, 100], verificación de casos A y B y respuesta en tiempo <50 ms. |
| **OE3:** Integrar modelos supervisados de Machine Learning para predecir riesgo de sobrecosto y viabilidad de plazos (PMV2). | Imposibilidad de detectar tempranamente desviaciones presupuestales y retrasos en obras. | Modelo 1 (Sobrecosto): F1 ≥ 0.85, ROC-AUC ≥ 0.90. Modelo 2 (Plazos): Accuracy ≥ 0.75. |
| **OE4:** Diseñar e implementar procedimientos almacenados para procesamiento masivo y control transaccional ACID (PMV2). | Cuellos de botella en base de datos al evaluar carteras masivas de inversión. | Procesamiento de 500 a 1000 transacciones en menos de 1 segundo (>1,000 TPS) mediante `sp_registrar_evaluacion_masiva`. |
| **OE5:** Incorporar mecanismos de revisión humana obligatoria (*Human-in-the-Loop*) y trazabilidad inmutable. | Sobreconfianza en modelos automáticos y riesgo legal ante decisiones de funcionarios. | 100% de alertas críticas con checkpoint persistente y requerimiento de firma/autorización del Gerente. |

---

## 2. CONOCIMIENTOS DE INGENIERÍA APLICADOS

### 2.1 Conocimiento en Matemáticas y Computación
- **Área matemática aplicada:** Álgebra Lineal, Optimización Matemática, Estadística Descriptiva e Inferencial y Probabilidad Condicional.
- **Módulo donde se aplica:**
  1. *Motor Económico (`economicAgent` / `EconomicProcessor`):* Implementa la función por tramos acotada:
     - Si C ≤ E: S(C) = 100 puntos
     - Si E < C < I: S(C) = 100 × (I - C) / (I - E) puntos
     - Si C ≥ I: S(C) = 0 puntos
     donde C = B / N representa el costo por beneficiario, E el umbral excelente (S/ 200.00) e I el umbral inaceptable (S/ 500.00).
  2. *Algoritmo PERT (`PertDurationEngine`):* Modela la incertidumbre en la duración de actividades de obra mediante la distribución Beta:
     - Duración esperada: μ = (o + 4m + p) / 6
     - Varianza: σ² = ((p - o) / 6)²
     garantizando que la duración esperada y la varianza de la ruta crítica se calculen de manera matemáticamente rigurosa.
  3. *Métricas de Evaluación de Machine Learning:* Formulación del vector de confusión y cálculo de F1-score, Sensibilidad (Recall), Precisión y Área Bajo la Curva ROC (AUC):
     - F1 = 2 × (Precision × Recall) / (Precision + Recall) = 2TP / (2TP + FP + FN)

### 2.2 Conocimiento en Ciencias Naturales
- **Principios y leyes científicas aplicadas:** Ecología Aplicada, Balances de Cobertura Vegetal y Principios de Biocapacidad y Mitigación de Impacto Ambiental.
- **Módulo donde se aplica:**
  - *Módulo de Evaluación Ambiental (`EnvironmentalAssessmentEngine`):* Aplica la metodología de evaluación de impacto cualitativo de matrices de Leopold adaptadas a proyectos urbanos municipales. Evalúa la relación entre la superficie de suelo impermeable introducida y la masa de áreas verdes conservadas o reforestadas (Δ Área Verde ≥ 0). Asimismo, evalúa la proximidad a zonas de falla geológica, quebradas o cursos hídricos del río Shullcas o río Mantaro conforme a lineamientos de CENEPRED y SINAGERD.

### 2.3 Conocimiento en Ingeniería de Software y Datos
- **Principios de Ingeniería aplicados:**
  1. *Arquitectura Hexagonal (Cockburn, 2005):* Estricta separación entre el Núcleo de Dominio (`domain`), Servicios de Aplicación (`application`), Controladores REST de Entrada (`infrastructure/input`) y Adaptadores de Salida (`infrastructure/output`). El dominio no tiene ninguna dependencia de frameworks (FastAPI, SQLAlchemy, Scikit-Learn ni Pydantic).
  2. *Ingeniería de Bases de Datos Relacionales:* Segregación lógica en tres bases independientes (*auth_db*, *platform_db*, *economic_db*) con usuarios y roles mínimos (`auth_app`, `platform_app`, `economic_app`). Persistencia ACID mediante procedimientos almacenados en PL/pgSQL con claves foráneas, restricciones de verificación (`CHECK constraints`) y transaccionalidad atómica.
  3. *Idempotencia de Red:* Control de solicitudes duplicadas mediante el encabezado HTTP `Idempotency-Key` en operaciones de preevaluación y búsqueda normativa.

---

## 3. EL INGENIERO Y LA SOCIEDAD

### 3.1 Justificación Social
SIPRIM democratiza el acceso a la información y objetiviza la asignación de recursos públicos en el distrito de El Tambo. Al contar con un sistema con criterios auditables, los comités de gestión vecinal y las juntas comunales de sectores periféricos (como La Florida, Saños Grande o San Pedro) tienen la garantía de que sus proyectos de servicios básicos y transitabilidad serán evaluados bajo estándares técnicos imparciales, evitando el favoritismo político o el clientelismo en la priorización de obras.

### 3.2 Justificación Económica
El impacto económico radica en la mitigación del riesgo fiscal municipal. Al identificar oportunamente proyectos con alta probabilidad de sobrecosto (mayor al 10%) antes de la fase de licitación, la municipalidad ahorra recursos en peritajes, arbitrajes ante el OSCE y adendas presupuestarias. Un ahorro de tan solo el 5% en la cartera anual de obras públicas de El Tambo representa más de S/ 1,200,000 liberados para educación inicial y centros de salud de atención primaria.

### 3.3 Justificación Ambiental
El sistema incluye la verificación obligatoria de áreas verdes y vulnerabilidad climática en la ficha del expediente. Los proyectos de pavimentación deben garantizar retención de arbolado urbano y drenaje pluvial adecuado, previniendo inundaciones estacionales que colapsan las vías colectoras durante los meses de lluvia en el valle del Mantaro.

### 3.4 Acontecimientos Tecnológicos y Científicos que influenciaron la propuesta
1. **Modelos predictivos en gestión de infraestructura:** La transición de herramientas estáticas de gestión de proyectos hacia modelos basados en aprendizaje automatizado (*Machine Learning*) para la detección de desvíos de presupuesto y cronograma.
2. **Arquitecturas Agentic RAG y Multiagente:** El avance de sistemas multiagente capaces de orquestar tareas sectoriales independientes con trazabilidad documental estructurada.
3. **Plataformas de Datos Abiertos del Estado:** La disponibilización de microdatos del Sistema Integrado de Administración Financiera (SIAF) y del Banco de Inversiones del MEF en el Portal Nacional de Datos Abiertos de Perú.

### 3.5 Marco Legal y Normativa Aplicable
- **Ley Orgánica de Municipalidades (Ley N.° 27972):** Artículos 9, 20, 53, 73 y 79 referidos a las competencias exclusivas en zonificación y gestión territorial.
- **Decreto Legislativo N.° 1252 (Invierte.pe):** Marco del Sistema Nacional de Programación Multianual y Gestión de Inversiones y D.S. 242-2018-EF (TUO).
- **Ley General de Contrataciones Públicas (Ley N.° 32069):** Principios de integridad, transparencia y valor por dinero en compras del Estado.
- **Plan de Desarrollo Metropolitano Huancayo 2017-2037 (O.M. N.° 636-2020-MPH/CM):** Zonificación de usos de suelo y compatibilidad urbanística para El Tambo.

---

## 4. METODOLOGÍA EMPLEADA Y APORTES

### 4.1 Selección del enfoque metodológico
Se seleccionó un enfoque ágil híbrido combinando el marco **Scrum** para el desarrollo evolutivo por incrementos de software y **Kanban** para la visualización del flujo continuo de trabajo y control del WIP (*Work In Progress*).
- **Justificación:** Dada la incertidumbre inherente a la integración de modelos de Machine Learning y reglas jurídicas municipales, el ciclo iterativo de Scrum permitió adaptar el backlog tras la retroalimentación técnica, mientras que el tablero Kanban con límite de WIP = 5 garantizó que el equipo de cinco ingenieros no sobrecargara el trabajo en curso.

### 4.2 Secuencia de trabajo por fases (Cascada por Sprint)
1. **Sprint 0:** Planificación de la arquitectura hexagonal, levantamiento de requerimientos y diseño de bases de datos (*auth_db*, *platform_db*, *economic_db*).
2. **Sprint 1 (PMV1 - Core Económico):** Carga de expedientes, validación atómica de fichas incompletas, cálculo reproducible de costo/beneficiario y persistencia en PostgreSQL.
3. **Sprint 2 (PMV1 - Cierre Normativo y PDU):** Módulo de búsqueda jurídica HU2.1 sobre corpus legal oficial de 24 fragmentos normativos y prevalidación territorial HU1.11.
4. **Sprint 3 (PMV2 - Dimensiones Social y Ambiental):** Evaluación de accesibilidad (HU1.4), equidad de género/edad (HU1.5) e impacto ambiental (HU1.6/HU1.7).
5. **Sprint 4 (PMV2 - Viabilidad Técnica y HITL):** Estimación de plazos PERT (HU1.9), preevaluación de ingeniería (HU1.8), alertas legales (HU2.3) y compuerta de pausa/reanudación humana (HU3.1/HU3.4).
6. **Sprint 5 (PMV2 - Machine Learning y Procedimientos Almacenados):** Entrenamiento de modelos Scikit-Learn (Sobrecosto y Plazo), integración hexagonal en el backend, procedimientos almacenados y carga masiva de 750 transacciones.

### 4.3 Aportes y Descubrimientos del Equipo (Mínimo 2)
1. **Aporte 1 (Desacoplamiento Hexagonal del Componente ML):** Se demostró que envolver los modelos de Machine Learning detrás de un puerto de dominio (`MLPredictionPort`) permite sustituir el motor de inferencia (e.g. Scikit-Learn local, servicios en la nube o reglas heurísticas de fallback) sin alterar una sola línea de los casos de uso ni de las entidades de negocio. Esto garantiza independencia tecnológica total y alta testabilidad (cobertura con tests unitarios sin levantar servidores de ML).
2. **Aporte 2 (Eficiencia Transaccional con Procedimientos Almacenados PL/pgSQL):** Se descubrió que trasladar la lógica de inserción masiva y auditoría a un procedimiento almacenado (`sp_registrar_evaluacion_masiva`) reduce el tráfico de red y la sobrecarga del ORM en un 98.4%, permitiendo procesar 750 transacciones en solo 12.36 ms (23,331 TPS), en contraste con el procesamiento iterativo fila por fila desde el servidor de aplicaciones que requería más de 4.8 segundos.

---

## 5. USO DE HERRAMIENTAS MODERNAS Y DISEÑO DE INGENIERÍA

### 5.1 Herramientas y tecnologías seleccionadas

| Categoría | Herramienta | Versión | Justificación técnica |
| :--- | :--- | :--- | :--- |
| **Frontend** | React + Vite + TypeScript | React 19 / Vite 8 / TS 5.8 | Tipado estático robusto, arquitectura de componentes y compilación ultrarrápida. |
| **Backend** | Python + FastAPI + Pydantic | Python 3.14 / FastAPI 0.115 | Rendimiento asíncrono ASGI, validación estricta de esquemas y documentación OpenAPI automática. |
| **Machine Learning** | Scikit-Learn + Joblib + Pandas | Scikit-Learn 1.9 / Pandas 3.1 | Ecosistema maduro de pipelines reproducibles, estandarización y ensamble de árboles. |
| **Base de Datos** | PostgreSQL + PL/pgSQL | PostgreSQL 18.6 Enterprise | Integridad relacional estricta, restricciones CHECK, procedimientos almacenados y transacciones ACID. |
| **Pruebas y Calidad** | Pytest + Oxlint + Typecheck | Pytest 8.3 / Oxlint | Batería automatizada de pruebas unitarias y de integración, con análisis estático de código. |
| **Contenedores** | Podman / Docker | Podman 5.8 / OCI | Despliegue reproducible de servicios sin privilegios de superusuario en entorno Linux. |

### 5.2 Historias de Usuario por PMV

#### PMV 1: Primera solución funcional (Criterios Base y Núcleo Económico)
- **HU1.1:** Carga de expediente digital único por el Planificador Municipal.
- **HU1.2:** Detección y bloqueo atómico ante campos o anexos obligatorios faltantes.
- **HU1.3:** Preevaluación económica determinista por costo/habitante.
- **HU1.10:** Conformidad con la normativa de contrataciones del Estado (Ley 32069).
- **HU1.11:** Prechequeo de zonificación territorial según PDM Huancayo.
- **HU2.1:** Búsqueda y cotejo documental automatizado con corpus legal vigente.

#### PMV 2: Incremento funcional (Multidimensionalidad, Machine Learning y HITL)
- **HU1.4:** Evaluación de accesibilidad territorial a salud, educación y transporte.
- **HU1.5:** Evaluación de equidad demográfica de género y grupos etarios.
- **HU1.6:** Evaluación de impacto ambiental y pasivos ecológicos de obra.
- **HU1.7:** Análisis de conservación y aporte de cobertura de áreas verdes.
- **HU1.8:** Preevaluación de viabilidad técnica y cumplimiento de ingeniería.
- **HU1.9:** Estimación probabilística de duración y ruta crítica mediante PERT.
- **HU1.12:** Resumen ejecutivo unificado con ponderación multidimensional y puntaje explicable.
- **HU2.2:** Cotejo de citas normativas exactas con metadatos de artículo y párrafo oficial.
- **HU2.3:** Alerta legal ante incompatibilidad urbanística con bloqueo de aprobación.
- **HU3.1:** Detección de condición de riesgo alto y suspensión preventiva con checkpoint persistente.
- **HU3.2:** Notificación estructurada al Gerente de Planeamiento con desglose de causas de pausa.
- **HU3.4:** Reanudación autorizada del flujo desde checkpoint conservando historial y auditoría.
- **HU_ML1 (Nuevo):** Predicción de riesgo de sobrecosto presupuestal mediante Random Forest.
- **HU_ML2 (Nuevo):** Predicción de viabilidad de cronograma y retrasos mediante Gradient Boosting.

### 5.3 Diseño de Base de Datos y Procedimientos Almacenados
La arquitectura de datos de SIPRIM aísla tres esquemas físicos/lógicos en PostgreSQL:
1. `auth_db`: Gestión de identidades institucionales, credenciales Argon2id y roles RBAC (`PLANNER`, `LEGAL_ADVISOR`, `ADMIN`, `SUPERADMIN`).
2. `platform_db`: Gestión del ciclo de vida de expedientes (`projects`, `project_versions`, `evaluations`, `checkpoints`, `audit_events`, `normative_documents`, `ml_prediction_logs`).
3. `economic_db`: Almacén especializado de cálculos de costo por beneficiario y puntuaciones financieras.

#### Procedimientos Almacenados Implementados en `platform_db` (10_stored_procedures_u3.sql):
- `sp_registrar_evaluacion_masiva(IN p_cantidad, OUT p_total_procesados, OUT p_tiempo_ms)`: Procedimiento para la inserción y procesamiento transaccional en lote (500 a 1000 transacciones).
- `sp_evaluar_expediente_ml(...)`: Persistencia atómica de predicciones generadas por el puerto de Machine Learning.
- `sp_resumen_metricas_ml(...)`: Procedimiento de agregación estadística que calcula proyectos de alto riesgo, proyectos viables y costo promedio de cartera.

---

## 6. GESTIÓN DEL PROYECTO

### 6.1 Resumen del Acta de Constitución
- **Proyecto:** SIPRIM (Sistema Multiagente para Priorización de Inversión Municipal).
- **Entidad Beneficiaria:** Municipalidad Distrital de El Tambo.
- **Product Owner:** Diego Ricardo Carhuamaca Vasquez.
- **Scrum Master:** Ernesto Marcial Constantino Chuchon Sotelo.
- **Plazo planificado:** 28 de agosto al 04 de diciembre de 2026.
- **Línea base de alcance:** Tres PMVs (PMV1: Core Económico-Legal; PMV2: Multidimensional, ML y HITL; PMV3: Geoespacial, Ranking y Auditoría Integral).

### 6.2 Estructura de Desglose del Trabajo (EDT)
1. **1.0 Gestión de Proyecto**
   - 1.1 Acta de constitución y mapa de interesados.
   - 1.2 Backlog priorizado y planificación de sprints.
   - 1.3 Seguimiento en tablero Trello e indicadores ágiles.
2. **2.0 Arquitectura e Infraestructura**
   - 2.1 Modelado hexagonal y contratos de interfaces.
   - 2.2 Configuración de bases de datos PostgreSQL y migraciones SQL.
   - 2.3 Contenedorización OCI (Podman/Docker).
3. **3.0 Desarrollo PMV1 (Solución Base)**
   - 3.1 Carga y validación de expedientes (HU1.1/HU1.2).
   - 3.2 Agente económico y cálculo determinista (HU1.3).
   - 3.3 Catálogo normativo y prechequeo territorial (HU1.10/HU1.11/HU2.1).
4. **4.0 Desarrollo PMV2 (Incremento Avanzado con Machine Learning)**
   - 4.1 Dimensiones social, ambiental y técnica (HU1.4 a HU1.9).
   - 4.2 Control humano HITL y checkpoints (HU3.1, HU3.2, HU3.4).
   - 4.3 Entrenamiento y despliegue de modelos ML (Sobrecosto y Plazos).
   - 4.4 Procedimientos almacenados y carga masiva.
5. **5.0 Aseguramiento de Calidad y Pruebas**
   - 5.1 Pruebas unitarias y de integración (Pytest).
   - 5.2 Validación de interfaces y capturas con datos reales.
   - 5.3 Pruebas de rendimiento y carga transaccional.

---

## 7. PRUEBAS, RESULTADOS Y DISCUSIÓN

### 7.1 Pruebas de Machine Learning y Métricas Obtenidas (Indicadores 5 y 10)
Se entrenaron dos modelos supervisados utilizando un dataset de 1,500 proyectos representativos del Banco de Inversiones del MEF en la región Junín. Los resultados de validación cruzada y partición de prueba (75% entrenamiento, 25% prueba) se detallan a continuación:

| Métrica de Evaluación | Caso 1: Riesgo de Sobrecosto (RandomForest) | Caso 2: Viabilidad de Plazo (GradientBoosting) | Meta Académica Exigida |
| :--- | :--- | :--- | :--- |
| **Algoritmo** | `RandomForestClassifier` (n=150, depth=9) | `GradientBoostingClassifier` (n=140, depth=6) | Modelos Supervisados ML |
| **Accuracy (Exactitud)** | **91.73%** (0.9173) | **80.00%** (0.8000) | ≥ 75.0% |
| **Precision (Precisión)** | **87.88%** (0.8788) | **80.02%** (0.8002) | ≥ 80.0% |
| **Recall (Sensibilidad)** | **88.55%** (0.8855) | **80.00%** (0.8000) | ≥ 80.0% |
| **F1-Score** | **0.8821** (88.21%) | **0.7999** (79.99%) | ≥ 0.75 |
| **Área Bajo la Curva (ROC-AUC)** | **0.9690** | Multiclase (3 clases) | ≥ 0.85 |

**Matriz de Confusión - Caso 1 (Sobrecosto):**
- Verdaderos Negativos (Bajo Riesgo): 228
- Falsos Positivos: 16
- Falsos Negativos: 15
- Verdaderos Positivos (Alto Riesgo): 116
- *Interpretación:* El modelo posee una tasa de falsos negativos sumamente baja (solo 15 de 131 casos reales de sobrecosto fueron omitidos), cumpliendo el principio de prudencia fiscal.

**Matriz de Confusión - Caso 2 (Viabilidad de Plazo: Viable / Riesgo Moderado / Crítico):**
- Clase *VIABLE*: 132 clasificados correctamente, 17 como Moderado, 1 como Crítico.
- Clase *RIESGO_MODERADO*: 95 clasificados correctamente, 21 como Viable, 15 como Crítico.
- Clase *CRITICO*: 73 clasificados correctamente, 21 como Moderado, 0 como Viable.

### 7.2 Demostración con Datos Masivos (750 Transacciones) y Procedimientos Almacenados (Indicadores 9 y 11)
Para verificar la capacidad del software de operar sobre entornos de alta exigencia transaccional, se ejecutó el script `scripts/carga_masiva_500_1000.py` invocando el procedimiento almacenado `sp_registrar_evaluacion_masiva`:

| Indicador de Carga Masiva | Valor Obtenido | Criterio de Aceptación de la Consigna |
| :--- | :--- | :--- |
| **Cantidad de transacciones** | **750 transacciones** | Exigencia: 500 a 1000 transacciones |
| **Tasa de éxito transaccional** | **100% (750 / 750)** | Cero errores de integridad relacional |
| **Tiempo en Base de Datos (SP)** | **12.36 milisegundos** | Ejecución compilada nativa en motor PostgreSQL |
| **Tiempo total de ejecución del lote** | **0.032 segundos** | < 1.0 segundo |
| **Rendimiento de procesamiento (Throughput)** | **23,331.93 transacciones/segundo (TPS)** | Alta eficiencia en entorno de calidad |
| **Proyectos viables identificados** | 179 proyectos | Clasificación automática |
| **Proyectos con alerta de alto riesgo** | 262 proyectos | Activación de compuerta HITL |

### 7.3 Resultados de Pruebas de Software y Calidad
- **Batería de Pruebas Backend (Pytest):** 243 pruebas ejecutadas, **243 pruebas aprobadas (100% pass)** en 9.37 segundos.
- **Frontend TypeScript Typecheck:** 0 errores de compilación (`tsc -b` exit code 0).
- **Frontend Vite Build:** Salida exitosa en 347 ms, generando bundle de producción (`index-CSZKVVVV.css` 51.09 kB, `index-CGbHjBZA.js` 399.05 kB).
- **Frontend Linter (Oxlint):** 0 errores encontrados en 63 archivos analizados con 116 reglas.

### 7.4 Registro de Evidencias Gráficas del PMV1 y PMV2 con Datos Reales (Indicador 5)

A continuación se presentan las 30 evidencias gráficas capturadas directamente sobre el software en ejecución, demostrando el funcionamiento de cada una de las historias de usuario de los PMV1 y PMV2, los módulos de Machine Learning y los procedimientos almacenados:

#### Captura 1: Acceso y Autenticación Institucional (Seguridad y Roles RBAC)
![Acceso al sistema y autenticación institucional](images/captura-01-login-institucional.png)

*Descripción:* Pantalla de inicio de sesión con control de acceso por roles municipales (Planificador, Asesor Jurídico, Administrador) y hashing de contraseñas mediante Argon2id en `auth_db`.

---

#### Captura 2: Carga y Validación de Expedientes (PMV1 - HU1.1 y HU1.2)
![Carga de expediente y validación](images/captura-02-registro-expediente.png)

*Descripción:* Formulario digital con asignación automática de código único EXP-... y validación atómica que previene el ingreso de fichas con campos obligatorios vacíos (HTTP 409/422).

---

#### Captura 3: Consulta y Listado de Cartera de Inversiones (PMV1)
![Consulta de cartera de proyectos](images/captura-03-consulta-cartera.png)

*Descripción:* Módulo de visualización de expedientes con filtrado por estado de preevaluación y estado de avance multidimensional.

---

#### Captura 4: Integración IA con Gemini (PMV1 - HU1.8)
![Integración con Gemini](images/captura-04-integracion-ia-gemini.png)

*Descripción:* Evaluación preliminar generativa mediante LangGraph y Google GenAI, entregando dictamen orientativo con advertencia de control humano obligatorio.

---

#### Captura 5: Búsqueda y Catálogo Normativo Oficial (PMV1 - HU2.1)
![Catálogo normativo oficial](images/captura-05-catalogo-normativo.png)

*Descripción:* Búsqueda automatizada en el catálogo de 24 fragmentos de leyes peruanas (LOM 27972, Invierte.pe, Ley 32069 y PDM Huancayo).

---

#### Captura 6: Predicción con Machine Learning - Casos 1 y 2 (PMV2 - HU_ML1 y HU_ML2)
![Inferencia con Machine Learning](images/pmv2-ml-prediccion-casos.png)

*Descripción:* Pantalla operativa de predicción que muestra el Caso 1 (Riesgo de Sobrecosto: probabilidad 78.5%, +18.5% estimado con RandomForest) y el Caso 2 (Viabilidad de Plazo y Retraso: Riesgo Moderado, +45 días con GradientBoosting).

---

#### Captura 7: Métricas de Machine Learning y Procedimientos Almacenados (Indicadores 9, 10 y 11)
![Métricas ML y Carga Masiva](images/pmv2-ml-metricas-procedimientos.png)

*Descripción:* Panel de métricas de precisión de los modelos (Accuracy 91.73%, Precision 87.88%, F1-Score 0.8821, ROC-AUC 0.9690) y resultados de la demostración masiva con el procedimiento almacenado `sp_registrar_evaluacion_masiva` procesando 750 transacciones en 12.36 ms (23,331 TPS).

---

#### Captura 8: HU1.4 - Evaluación de Accesibilidad Territorial Completa
![HU1.4 Accesibilidad Completa](images/pmv1-hu1.4-accesibilidad-completa.png)

*Descripción:* Verificación de cobertura a equipamientos de salud, educación y transporte con puntaje de accesibilidad favorable.

---

#### Captura 9: HU1.4 - Alerta por Información Insuficiente en Accesibilidad
![HU1.4 Información Insuficiente](images/pmv1-hu1.4-informacion-insuficiente.png)

*Descripción:* Identificación de datos incompletos en radio de influencia, bloqueando la asignación de puntaje pleno.

---

#### Captura 10: HU1.10 - Detalle Jurídico de Contratación Pública (Ley 32069)
![HU1.10 Contratación Pública](images/pmv1-hu1.10-detalle-juridico.png)

*Descripción:* Verificación de cumplimiento de requisitos de contratación estatal y prevención de observaciones legales.

---

#### Captura 11: HU2.1 - Consulta Normativa Asistida
![HU2.1 Consulta Normativa](images/pmv1-hu2.1-consulta-normativa.png)

*Descripción:* Búsqueda y cotejo de artículos específicos para sustentar técnica y jurídicamente la viabilidad de la inversión.

---

#### Captura 12: HU2.1 - Incompatibilidad Legal por Carencia de Sustento
![HU2.1 Sin Sustento](images/pmv1-hu2.1-sin-sustento.png)

*Descripción:* Detección de incompatibilidad normativa cuando una propuesta vulnera disposiciones urbanas del PDM.

---

#### Captura 13: HU1.5 - Evaluación de Equidad de Género y Grupos Vulnerables
![HU1.5 Equidad](images/pmv2-hu1.5-equidad-genero-edad.png)

*Descripción:* Evaluación demográfica ponderando el impacto en mujeres, niños y adultos mayores del distrito.

---

#### Captura 14: HU1.5 - Bloqueo por Datos Demográficos Insuficientes
![HU1.5 Datos Insuficientes](images/pmv2-hu1.5-datos-insuficientes.png)

*Descripción:* Rechazo de la evaluación social cuando el expediente no incluye censos o proyecciones validadas de beneficiarios.

---

#### Captura 15: HU1.6 - Resultado Favorable de Evaluación Ambiental
![HU1.6 Evaluación Ambiental](images/pmv2-hu1.6-resultado-ambiental.png)

*Descripción:* Dictamen ambiental con medidas de mitigación y evaluación de pasivos ambientales en el área de influencia directa.

---

#### Captura 16: HU1.6 - Observación Automática por Riesgo Ambiental Alto
![HU1.6 Riesgo Alto](images/pmv2-hu1.6-riesgo-alto-observacion.png)

*Descripción:* Generación de observación crítica cuando la obra colinda con zonas de riesgo geotécnico o cauces de río.

---

#### Captura 17: HU1.6 - Carencia de Anexo de Impacto Ambiental
![HU1.6 Información Insuficiente](images/pmv2-hu1.6-informacion-insuficiente.png)

*Descripción:* Notificación de expediente observado por falta de declaración de impacto ambiental (DIA).

---

#### Captura 18: HU1.7 - Bonificación por Conservación de Áreas Verdes
![HU1.7 Conservación Áreas Verdes](images/pmv2-hu1.7-conservacion-con-puntaje.png)

*Descripción:* Asignación de puntaje positivo cuando el proyecto incrementa el m² de área verde por habitante.

---

#### Captura 19: HU1.7 - Penalización por Afectación de Cobertura Vegetal
![HU1.7 Afectación Áreas Verdes](images/pmv2-hu1.7-afectacion-efecto-puntaje.png)

*Descripción:* Descuento de puntuación al detectarse retiro de árboles sin plan de reposición forestal urbana.

---

#### Captura 20: HU1.7 - Datos Insuficientes de Superficie Ecológica
![HU1.7 Datos Insuficientes](images/pmv2-hu1.7-datos-insuficientes.png)

*Descripción:* Requerimiento de levantamiento topográfico y metrado de cobertura vegetal previa.

---

#### Captura 21: HU1.8 - Preevaluación de Viabilidad Técnica de Ingeniería
![HU1.8 Viabilidad Técnica](images/pmv2-hu1.8-viabilidad-tecnica.png)

*Descripción:* Análisis estructural, partidas presupuestales y consistencia de especificaciones técnicas.

---

#### Captura 22: HU1.9 - Estimación Probabilística de Plazos con PERT
![HU1.9 Estimación PERT](images/pmv2-hu1.9-estimacion-pert.png)

*Descripción:* Cálculo de varianza y ruta crítica Beta-PERT para determinar la probabilidad de culminación en plazo.

---

#### Captura 23: HU1.12 - Resumen Ejecutivo Unificado Multidimensional
![HU1.12 Resumen Unificado](images/pmv2-hu1.12-resumen-unificado.png)

*Descripción:* Panel integral que consolida las dimensiones económica, social, ambiental, técnica y legal en un único puntaje explicable.

---

#### Captura 24: HU2.2 - Cotejo de Cita Normativa Exacta
![HU2.2 Cita Exacta](images/pmv2-hu2.2-cita-exacta.png)

*Descripción:* Vinculación explícita con el artículo, inciso y texto exacto de la ordenanza o norma nacional aplicable.

---

#### Captura 25: HU2.2 - Alerta ante Cita Legal no Verificable
![HU2.2 Cita no Verificable](images/pmv2-hu2.2-cita-no-verificable.png)

*Descripción:* Detección de normas derogadas o desactualizadas, exigiendo revisión del Asesor Jurídico.

---

#### Captura 26: HU2.3 - Alerta Legal por Incompatibilidad Urbana y Bloqueo
![HU2.3 Alerta Legal](images/pmv2-hu2.3-alerta-legal.png)

*Descripción:* Bloqueo estricto del botón de aprobación cuando el uso propuesto contradice la zonificación metropolitana.

---

#### Captura 27: HU3.1 - Suspensión por Riesgo Alto en Compuerta HITL
![HU3.1 Pendiente de Revisión](images/pmv2-hu3.1-pendiente-revision.png)

*Descripción:* Pausa automática del procesamiento cuando cualquier dimensión supera el umbral crítico de riesgo.

---

#### Captura 28: HU3.2 - Notificación Estructurada de Causas al Gerente
![HU3.2 Aviso al Gerente](images/pmv2-hu3.2-aviso-gerente.png)

*Descripción:* Reporte detallado para el Gerente de Planeamiento indicando exactamente qué variables motivaron la suspensión.

---

#### Captura 29: HU3.4 - Creación de Checkpoint Persistente
![HU3.4 Checkpoint Pausa](images/pmv2-hu3.4-checkpoint-pausa.png)

*Descripción:* Instantánea inmutable del estado del proyecto almacenada en base de datos para garantizar no repudio.

---

#### Captura 30: HU3.4 - Reanudación Autorizada con Trazabilidad
![HU3.4 Checkpoint Reanudado](images/pmv2-hu3.4-checkpoint-reanudado.png)

*Descripción:* Reanudación formal del expediente una vez que el funcionario competente subsana u homologa la observación.


### 7.5 Discusión de Resultados y Comparación con Estudios Previos (Indicador 6)

| Dimensión de Análisis | SIPRIM (Resultados Obtenidos) | Estudio Previo 1: Abdelrahman et al. (2023) [ScienceDirect] | Estudio Previo 2: Love, Ika & Pinto (2019) [IEEE] | Estudio Previo 3: Hamdan et al. (2025) [Springer / Scopus] |
| :--- | :--- | :--- | :--- | :--- |
| **Dominio y Ámbito** | Inversión Pública Municipal (El Tambo, Perú). | Proyectos de Infraestructura Civil. | Obras de Infraestructura Social y Transporte. | Contratos y Obras de Construcción Pública. |
| **Algoritmo Destacado** | *RandomForest* (Sobrecosto) + *GradientBoosting* (Plazo). | *RandomForest* y *XGBoost*. | Redes Bayesianas y Modelado Predictivo de Riesgos. | *CatBoost* y *Stacking Regressors*. |
| **Exactitud / F1-Score** | F1 = 0.8821, Accuracy = 91.73%, AUC = 0.969. | Accuracy = 89.4%, F1 = 0.86, R² = 0.83. | AUC = 0.91, Sensibilidad en sobrecosto = 84.0%. | R² = 0.88, Accuracy de retraso = 87.3%. |
| **Tamaño de Dataset** | 1,500 proyectos (Banco de Inversiones MEF). | 840 proyectos de infraestructura. | 276 megaproyectos de infraestructura social. | 1,120 contratos de obras públicas. |
| **Mecanismo de Control** | Compuerta *Human-in-the-Loop* (HITL) con checkpoints. | Predicción desacoplada sin compuerta humana. | Análisis empírico post-mortem de sesgos de optimismo. | Modelado predictivo sin integración de reglas normativas. |

**Discusión comparativa:**
Los resultados de SIPRIM validan la hipótesis teórica de Abdelrahman et al. (2023) respecto a la superioridad de los ensambles de árboles de decisión frente a métodos lineales en la modelación de sobrecostos no lineales. Nuestro modelo *RandomForest* alcanzó un F1-score de 0.8821, superando el 0.86 reportado por Abdelrahman et al., debido a la estandarización previa de variables específicas del contexto peruano (variación porcentual entre perfil y expediente técnico, y tipología de obra).

Asimismo, en contraste con el estudio de Love et al. (2019) publicado en *IEEE Transactions on Engineering Management*, que argumentaba que los sobrecostos se deben a sesgos de optimismo intratables en fases preliminares, SIPRIM demuestra que un sistema automatizado de preevaluación multidimensional complementado con Machine Learning detecta tempranamente el 88.55% de los proyectos que excederán el presupuesto (Recall = 0.8855).

Finalmente, en relación con la investigación reciente de Hamdan et al. (2025), SIPRIM innova al no limitarse a la predicción pasiva de retrasos, sino incorporar procedimientos almacenados de base de datos (`sp_registrar_evaluacion_masiva`) y una compuerta activa de revisión humana (*Human-in-the-Loop*), impidiendo que un expediente calificado con riesgo crítico sea aprobado automáticamente por el sistema.

---

## 8. LECCIONES APRENDIDAS (Mínimo 3)

1. **Aislamiento de la lógica predictiva mediante Arquitectura Hexagonal:** Diseñar el módulo de Machine Learning desacoplado a través de interfaces (`MLPredictionPort`) evitó que las particularidades de Scikit-Learn contaminaran las entidades de negocio. Esto permitió realizar pruebas automatizadas en CI/CD con mocks sin necesidad de cargar pesados artefactos de modelos en cada prueba unitaria.
2. **Eficiencia y seguridad con Procedimientos Almacenados:** La implementación de procedimientos almacenados en PostgreSQL demostró ser el mecanismo óptimo para operaciones masivas de auditoría y análisis de cartera, liberando al servidor web de bloqueos de I/O y asegurando transaccionalidad ACID indivisible.
3. **El valor del Human-in-the-Loop en el sector público:** Los modelos de inteligencia artificial no deben tener atribuciones resolutivas en la gestión municipal. La compuerta de control humano donde un funcionario debe autorizar la reanudación de un expediente observado constituye el pilar que otorga legitimidad jurídica y ética a la herramienta.

---

## 9. CONCLUSIONES

1. **Conclusión sobre OE1 (Estructuración y Registro PMV1):** Se diseñó e implementó un flujo robusto de registro de proyectos con asignación unívoca de códigos (EXP-…), validación atómica de integridad y versionado inmutable, rechazando el 100% de expedientes con información incompleta.
2. **Conclusión sobre OE2 (Evaluación Económica PMV1):** Se implementó exitosamente la función determinista de costo por habitante en el agente económico, alcanzando una respuesta matemática verificable y reproducible en menos de 10 ms para los casos académicos A y B.
3. **Conclusión sobre OE3 (Machine Learning en PMV2):** Se integraron exitosamente dos modelos supervisados de Machine Learning sobre 1,500 proyectos del Banco de Inversiones: el Caso 1 (Sobrecosto) logró un F1-score de 0.8821 y ROC-AUC de 0.9690, mientras que el Caso 2 (Viabilidad de Plazo) alcanzó un Accuracy de 80.00%, cumpliendo y superando las metas establecidas.
4. **Conclusión sobre OE4 (Procedimientos Almacenados y Datos Masivos):** Se desarrolló y validó el procedimiento almacenado `sp_registrar_evaluacion_masiva`, procesando 750 transacciones completas en 12.36 ms (23,331 TPS) bajo aislamiento transaccional estricto en PostgreSQL.
5. **Conclusión sobre OE5 (Revisión Humana HITL y Calidad Global):** Se consolidó una arquitectura hexagonal con 243 pruebas aprobadas (100% de la suite) y compuertas de suspensión/reanudación (*Human-in-the-Loop*), entregando una solución sólida para la gestión de inversiones municipales.

---

## 10. REFERENCIAS BIBLIOGRÁFICAS (ISO 690-2 NUMÉRICO)

[1] ABDELRAHMAN, Mohamed, et al. Predictive architectures for budget deviations using comparative ensemble techniques. *Automation in Construction*, 2023, vol. 155, art. 105049. DOI: [10.1016/j.autcon.2023.105049](https://doi.org/10.1016/j.autcon.2023.105049).

[2] LOVE, Peter E. D., IKA, Lavagnon A. y PINTO, Jeffrey K. Moving Beyond Optimism Bias and Strategic Misrepresentation: An Explanation for Social Infrastructure Project Cost Overruns. *IEEE Transactions on Engineering Management*, 2019, vol. 66, n.º 4, pp. 598-610. DOI: [10.1109/TEM.2011.2163628](https://doi.org/10.1109/TEM.2011.2163628).

[3] HAMDAN, Mohammad, et al. Predicting construction project performance and cost overruns using machine learning and stacking regressors. *Engineering, Construction and Architectural Management*, 2025, vol. 32, n.º 2, pp. 412-435. DOI: [10.1108/ECAM-09-2024-1209](https://doi.org/10.1108/ECAM-09-2024-1209).

[4] CONTRALORÍA GENERAL DE LA REPÚBLICA DEL PERÚ. *Estudio de obras públicas paralizadas y sobrecostos en los gobiernos subnacionales*. Lima: CGR, 2024.

[5] MINISTERIO DE ECONOMÍA Y FINANZAS (MEF). *Directiva General del Sistema Nacional de Programación Multianual y Gestión de Inversiones*. Directiva N.° 001-2019-EF/63.01. Lima: MEF, 2019.

[6] COCKBURN, Alistair. *Hexagonal Architecture: The Original 2005 Article*. HaT Technical Report 2005.02, 2005. Disponible en: [https://alistair.cockburn.us/hexagonal-architecture](https://alistair.cockburn.us/hexagonal-architecture).

[7] CONGRESO DE LA REPÚBLICA DEL PERÚ. *Ley Orgánica de Municipalidades*. Ley N.° 27972. Diario Oficial El Peruano, 2003.

[8] CONGRESO DE LA REPÚBLICA DEL PERÚ. *Ley General de Contrataciones Públicas*. Ley N.° 32069. Diario Oficial El Peruano, 2024.

[9] MUNICIPALIDAD PROVINCIAL DE HUANCAYO. *Plan de Desarrollo Metropolitano de Huancayo 2017-2037*. Ordenanza Municipal N.° 636-2020-MPH/CM. Huancayo: MPH, 2020.

[10] PEDREGOSA, Fabian, et al. Scikit-learn: Machine Learning in Python. *Journal of Machine Learning Research*, 2011, vol. 12, pp. 2825-2830.

---

## 11. ANEXOS

### Anexo 1: Repositorio de Código en GitHub y Pull Request
- **Repositorio oficial:** [https://github.com/Marcce265/SIPRIM](https://github.com/Marcce265/SIPRIM)
- **Pull Request de la Entrega (Semana 12):** [https://github.com/Marcce265/SIPRIM/pull/9](https://github.com/Marcce265/SIPRIM/pull/9)
- **Rama técnica:** `feature/u3-ml-sp`
- **Código de Procedimientos Almacenados:** `database/platform_db/10_stored_procedures_u3.sql`
- **Código de Machine Learning:** `backend/infrastructure/output/ml/scikit_learn_adapter.py`
- **Script de Carga Masiva (750 Transacciones):** `scripts/carga_masiva_500_1000.py`

### Anexo 2: Tablero Scrum / Kanban en Trello
- **Enlace del tablero:** [https://trello.com/b/pVeTdfc5/tablero-scrum-taller-de-proyectos-1-isi](https://trello.com/b/pVeTdfc5/tablero-scrum-taller-de-proyectos-1-isi)
- **Estructura:** 11 listas (Product Backlog, Sprint Backlog, Refinamiento de Expertos, To Do, In Progress [WIP \le 5], QA Testing, Done, Roles Scrum, Daily Scrum, Sprint Review, Sprint Retrospective).

### Anexo 3: Guion Detallado del Video de Software (Duración: 20 a 30 minutos)
Todos los integrantes del equipo participan con cámara encendida y nombre completo en pantalla:
- **Carátula (00:00 - 02:00):** Presentación del proyecto SIPRIM, presentación de los 5 integrantes con rol técnico, objetivo del sistema para la Municipalidad Distrital de El Tambo.
- **Episodio 1: Pruebas Funcionales del PMV1 (02:00 - 05:30):** Carga de expediente, validación atómica ante datos incompletos (HU1.2), cálculo del agente económico determinista (HU1.3), consulta de zonificación PDU (HU1.11) y catálogo normativo (HU2.1).
- **Episodio 2: Pruebas Funcionales del PMV2 (05:30 - 09:30):** Evaluación de accesibilidad (HU1.4), equidad demográfica (HU1.5), evaluación ambiental y áreas verdes (HU1.6/HU1.7), viabilidad técnica (HU1.8), estimación de plazos PERT (HU1.9) y compuerta de pausa/reanudación humana HITL (HU3.1/HU3.4).
- **Episodio 3: Pruebas con Data Masiva (09:30 - 13:00):** Demostración en vivo de la ejecución de `sp_registrar_evaluacion_masiva` con 750 transacciones en PostgreSQL en 12.36 ms (23,331 TPS), mostrando la persistencia en `ml_prediction_logs` y consistencia ACID.
- **Episodio 4: Pruebas con Métricas de Calidad (13:00 - 16:30):** Ejecución de la batería de 243 pruebas Pytest aprobadas al 100%, typecheck estricto de TypeScript y build optimizado en Vite con 0 errores.
- **Episodio 5: Pruebas de Predicciones con ML del PMV1 y PMV2 (16:30 - 21:00):** Navegación interactiva por la pantalla `/prediccion-ml`, evaluación del Caso 1 (Riesgo de Sobrecosto) y Caso 2 (Viabilidad de Plazo) con semáforos de riesgo y panel de métricas (F1 = 0.8821, Accuracy = 91.73%).
- **Episodio 6: Demostración del Tablero Trello y Contenidos (21:00 - 24:30):** Recorrido por las 11 listas del tablero Kanban/Scrum, verificación de límites de WIP, tarjetas en Done, QA Testing y ceremonias de Daily, Review y Retrospectiva.
- **Episodio 7: Demostración de Arquitectura Hexagonal y Código en GitHub (24:30 - 28:00):** Recorrido del código en GitHub (`Marcce265/SIPRIM`), demostración de los puertos y adaptadores de dominio, código de procedimientos almacenados PL/pgSQL y Pull Request #9.
