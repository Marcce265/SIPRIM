# FACULTAD DE INGENIERÍA
## Escuela Académico Profesional de Ingeniería de Sistemas e Informática

**ASIGNATURA:** TALLER DE PROYECTOS 1 - ISI  
**DOCENTE:** GUEVARA JIMENEZ, JORGE ALFREDO  
**UNIDAD:** III &nbsp;|&nbsp; **SEMANA:** 12  
**FECHA DE ENTREGA:** Noviembre de 2026 &nbsp;|&nbsp; **NRC:** [NRC de Asignatura]  

---

# SIPRIM
### Sistema Multiagente para la Priorización de Proyectos de Inversión Municipal empleando Machine Learning, Arquitectura Hexagonal y Procedimientos Almacenados
**Ámbito institucional de aplicación:** Municipalidad Distrital de El Tambo, Huancayo, Junín  

| Integrante | Rol Scrum | Rol Técnico Principal |
| :--- | :--- | :--- |
| **Carhuamaca Vasquez, Diego Ricardo** | Product Owner | Desarrollo Backend y Lógica de Negocio |
| **Chuchon Sotelo, Ernesto Marcial Constantino** | Scrum Master | Arquitectura de Software y Modelado UML |
| **Huachos Lopez, Madelyn** | Scrum Team | Desarrollo Frontend e Interfaces de Usuario |
| **Reinaga Cisneros, Hermiluz Deyanira** | Scrum Team | Base de Datos y Procedimientos Almacenados |
| **Sierra Leiva, Piero Martin** | Scrum Team | Integración IA / Machine Learning y APIs |

---

## RESUMEN EJECUTIVO
*(Extensión estricta: 242 palabras)*

El proyecto SIPRIM tuvo como objetivo diseñar, implementar y validar un sistema de soporte a la toma de decisiones para la preevaluación y priorización multidimensional de proyectos de inversión pública en la Municipalidad Distrital de El Tambo. El sistema aborda la fragmentación y falta de trazabilidad en la revisión de expedientes municipales mediante una arquitectura hexagonal desacoplada, integrada con modelos supervisados de Machine Learning y procedimientos almacenados transaccionales en PostgreSQL. 

Durante el ciclo de desarrollo correspondiente a los Productos Mínimos Viables PMV1 y PMV2, se construyó una aplicación con frontend en React, TypeScript y Vite, y un backend estructurado en FastAPI bajo arquitectura hexagonal (puertos y adaptadores), persistiendo en tres bases lógicas relacionales: *auth_db*, *platform_db* y *economic_db*. Se entrenaron e integraron dos modelos de Machine Learning utilizando scikit-learn sobre un dataset de 1,500 iniciativas basado en el Banco de Inversiones (Invierte.pe): Caso 1 (Riesgo de Sobrecosto mediante *RandomForestClassifier*, obteniendo Accuracy de 91.73%, Precision de 87.88%, Recall de 88.55%, F1-score de 0.8821 y ROC-AUC de 0.9690) y Caso 2 (Viabilidad de Plazo y Retraso mediante *GradientBoostingClassifier*, con Accuracy de 80.00% y F1-score de 0.7999). 

Asimismo, se implementó el procedimiento almacenado transaccional `sp_registrar_evaluacion_masiva`, validando el rendimiento con una demostración de 750 transacciones ejecutadas en 12.36 ms (23,331 transacciones/segundo) con cumplimiento estricto de propiedades ACID. La suite de pruebas automatizadas alcanzó 243 pruebas aprobadas (100% de la batería pytest), logrando una solución orientativa explicable con control humano activo (*Human-in-the-Loop*).

**Palabras clave:** Machine Learning, Arquitectura Hexagonal, Inversión Pública Municipal, Invierte.pe, Procedimientos Almacenados, Priorización de Proyectos.

---

## ABSTRACT
*(Word count: 228 words)*

The SIPRIM project aimed to design, implement, and validate a decision-support system for the multidimensional pre-evaluation and prioritization of municipal public investment projects in the District Municipality of El Tambo, Peru. The system addresses the fragmentation, lack of traceability, and delay in reviewing municipal project files through a decoupled hexagonal architecture integrated with supervised Machine Learning models and transactional stored procedures in PostgreSQL.

During the development cycle of Minimum Viable Products MVP1 and MVP2, a full-stack solution was developed using React, TypeScript, and Vite on the client side, and FastAPI under hexagonal architecture (ports and adapters) on the server side, persisting across three logical databases (*auth_db*, *platform_db*, and *economic_db*). Two machine learning models were trained and deployed using scikit-learn on a 1,500-project dataset derived from Peru's National Public Investment System (Invierte.pe): Use Case 1 (Cost Overrun Risk using *RandomForestClassifier*, achieving 91.73% Accuracy, 87.88% Precision, 88.55% Recall, 0.8821 F1-score, and 0.9690 ROC-AUC) and Use Case 2 (Schedule Feasibility and Delay Prediction using *GradientBoostingClassifier*, achieving 80.00% Accuracy and 0.7999 F1-score). Furthermore, a PL/pgSQL transactional stored procedure was engineered to execute bulk assessments, successfully processing 750 transactions in 12.36 ms (23,331 TPS) with complete ACID integrity. The backend automated test suite reached 243 passing tests (100%), consolidating an explainable, Human-in-the-Loop municipal solution.

**Keywords:** Machine Learning, Hexagonal Architecture, Public Municipal Investment, Stored Procedures, Project Prioritization, Invierte.pe.

---

## 1. ANÁLISIS DE PROBLEMAS

### 1.1 Identificación y formulación del problema
La Municipalidad Distrital de El Tambo, en la provincia de Huancayo, administra anualmente una cartera de inversión pública que abarca más de 60 iniciativas orientadas al cierre de brechas urbanas en transitabilidad vial, saneamiento, educación y seguridad ciudadana. De acuerdo con informes de la Contraloría General de la República (2023), los gobiernos locales presentan una tasa de retraso contractual que supera el 68% de las obras iniciadas y sobrecostos presupuestales que promedian el 22.4% del valor referencial debido a deficiencias no detectadas en los expedientes técnicos iniciales.

En el contexto operativo de El Tambo, la formulación del problema complejo se sintetiza en la siguiente interrogante de ingeniería:
> *¿Cómo diseñar e implementar una solución de software inteligente que permita automatizar la preevaluación técnica, económica, social y ambiental de expedientes de inversión municipal, anticipar mediante Machine Learning el riesgo de sobrecosto y retraso, y garantizar la trazabilidad de las decisiones públicas con compuertas de control humano y rendimiento transaccional masivo?*

### 1.2 Árbol de Problemas
Para modelar las causas raíz, el problema focal y las ramificaciones de impacto en la sociedad, se diseñó el **Árbol de Problemas** de la inversión municipal en El Tambo:

![Árbol de Problemas](images/diagrama-arbol-problemas.png)

#### Análisis de relaciones causa-efecto:
1. **Problema Central:** Deficiente, subjetivo y tardío proceso de evaluación y priorización de expedientes de proyectos de inversión pública en la Municipalidad Distrital de El Tambo.
2. **Efectos Directos (Nivel 1):**
   - Retrasos severos de 6 a 18 meses en la entrega física de obras públicas municipales.
   - Sobrecostos presupuestales imprevistos (adicionales de obra que exceden el 20% del monto de adjudicación).
   - Paralización de obras por observaciones ambientales no subsanadas o vicios de contratación bajo la Ley 32069.
3. **Efectos Indirectos (Impacto Final):**
   - Pérdida de confianza ciudadana e incremento de la conflictividad vecinal en anexos periurbanos de El Tambo.
   - Perjuicio económico al erario distrital y alto costo de oportunidad de los recursos del canon y foncomun.
   - Persistencia de brechas críticas en servicios de agua, desagüe, pistas y veredas.
4. **Causas Directas:**
   - **C1:** Revisión manual de expedientes en la OPMI lenta (4 a 6 horas por expediente) y sujeta a discrecionalidad.
   - **C2:** Inexistencia de herramientas de Machine Learning para predecir sobrecostos y retrasos antes de licitar.
   - **C3:** Criterios evaluativos dispersos en silos aislados sin una función multicriterio unificada.
   - **C4:** Carencia de mecanismos de trazabilidad, auditoría y compuertas de control humano (*Human-in-the-Loop* - HITL).
5. **Causas Raíz (Subcausas de Ingeniería):**
   - Empleo de hojas de cálculo aisladas sin validación sintáctica de datos en tiempo real.
   - Falta de aprovechamiento analítico de los datos abiertos del Banco de Inversiones del MEF (Invierte.pe).
   - Reglamentación compleja de la Ley 32069 de Contrataciones del Estado no sistematizada en la revisión técnica.
   - Decisiones de priorización sin registro criptográfico ni bitácora de auditoría inalterable.

### 1.3 Línea base, metas y evidencia verificable

| Indicador Clave | Línea Base (Situación Inicial) | Meta al Cierre (PMV2 / PMV3) | Resultado Obtenido en Semana 12 | Evidencia Verificable |
| :--- | :--- | :--- | :--- | :--- |
| **Tiempo de revisión por expediente** | 4 a 6 horas por expediente técnico | Menor a 5 minutos por expediente | **< 2 segundos (Inferencia ML < 10 ms)** | Módulo `/prediccion-ml` en frontend |
| **Capacidad de procesamiento masivo** | 10 a 15 proyectos por semana (manual) | 500 a 1000 transacciones en lote | **750 transacciones en 12.36 ms (23,331 TPS)** | Stored Procedure `sp_registrar_evaluacion_masiva` |
| **Exactitud de predicción de sobrecosto** | 0% (No se predecía, reactivo) | Accuracy > 80% en validación | **Accuracy 91.73%, ROC-AUC 0.9690** | Modelo Random Forest serializado en joblib |
| **Exactitud de viabilidad de plazos** | 0% (Estimaciones intuitivas) | F1-Score > 75% | **Accuracy 80.00%, F1-Score 0.7999** | Modelo Gradient Boosting en Colab |
| **Cobertura multidimensional** | 1 dimensión aislada (costo) | 5 dimensiones integradas | **5 dimensiones (Económica, Social, Ambiental, Legal, Plazos)** | Entidades y DTOs del dominio hexagonal |
| **Trazabilidad y control humano** | Nula (firmas dispersas en papel) | 100% de alertas con registro HITL | **100% de pausas registradas con hash SHA-256** | Tabla `solicitudes_revision_hitl` en PostgreSQL |

### 1.4 Objetivos del proyecto

#### Objetivo General
Diseñar e implementar un sistema de soporte a la toma de decisiones para la preevaluación y priorización multidimensional de proyectos de inversión pública en la Municipalidad Distrital de El Tambo, integrando modelos supervisados de Machine Learning, arquitectura hexagonal en FastAPI y procedimientos almacenados transaccionales en PostgreSQL.

#### Objetivos Específicos
1. **OE1:** Desarrollar el núcleo de persistencia relacional y lógica transaccional mediante PostgreSQL y Procedimientos Almacenados (PL/pgSQL), garantizando atomicidad (ACID) y soporte para cargas masivas superiores a 500 transacciones.
2. **OE2:** Entrenar, validar e implementar dos modelos de Machine Learning supervisados (Random Forest Classifier y Gradient Boosting Classifier) basados en datos del Banco de Inversiones del MEF, para predecir el riesgo de sobrecosto presupuestal y la clase de viabilidad/retraso de obra.
3. **OE3:** Diseñar y construir el backend de la aplicación bajo los principios de la Arquitectura Hexagonal (Puertos y Adaptadores) en Python/FastAPI, desacoplando completamente el dominio y los casos de uso de las fuentes de datos y frameworks externos.
4. **OE4:** Desarrollar una interfaz de usuario reactiva, accesible y modular en React 18, TypeScript y TailwindCSS, que incorpore compuertas de control humano (*Human-in-the-Loop* - HITL) ante alertas normativas de la Ley 32069.
5. **OE5:** Ejecutar pruebas de integración, rendimiento y cobertura automatizada (suite pytest) que verifiquen el cumplimiento del 100% de los criterios funcionales de los PMV1 y PMV2.

---

## 2. CONOCIMIENTOS DE INGENIERÍA APLICADOS

### 2.1 Conocimiento en Matemáticas y Computación
- **Álgebra Lineal y Teoría de Matrices:** Empleada en la vectorización de atributos continuos y categóricos de los proyectos para el entrenamiento matricial de los estimadores de Machine Learning en `scikit-learn`.
- **Probabilidad y Estadística Inferencial:** Modelado de distribuciones probabilísticas continuas y estimación de tiempos de obra mediante el método PERT (Program Evaluation and Review Technique), calculando la duración esperada y la varianza mediante:
  `μ = (o + 4m + p) / 6,    σ² = ((p - o) / 6)²`
- **Algoritmos de Ensamble y Aprendizaje Supervisado:** 
  - *Random Forest:* Bosques aleatorios con 100 árboles de decisión que reducen la varianza mediante bagging y votación mayoritaria para predecir sobrecostos.
  - *Gradient Boosting:* Optimización recursiva sobre funciones de pérdida diferenciables mediante boosting para clasificar retrasos de proyectos.
- **Teoría de Decisión Multicriterio y Ponderación Determinista:**
  `S(C) = Σ (w_i · c_i),  sujeto a  Σ w_i = 100%`

### 2.2 Conocimiento en Ciencias Naturales
- **Evaluación de Impacto Ambiental y Factores Ecológicos:** Se integraron criterios de conservación de cobertura vegetal nativa del valle del Mantaro, zonificación de riesgo ante inundaciones por la cuenca del río Shullcas y gestión de pasivos ambientales en proyectos de infraestructura, traduciendo variables ecológicas en penalizaciones o bonificaciones objetivas dentro del algoritmo de priorización.

### 2.3 Conocimiento en Ingeniería de Software y Datos
- **Arquitectura Hexagonal (Cockburn, 2005):** Aislamiento del núcleo de negocio (Domain) mediante puertos (Ports) e interfaces, desacoplándolo de controladores REST (FastAPI) y adaptadores de infraestructura (PostgreSQL, Scikit-learn, Gemini).
- **Normalización de Bases de Datos Relacionales (3FN):** Separación de esquemas lógicos en PostgreSQL (`auth_db`, `platform_db`, `economic_db`) garantizando integridad referencial, índices B-Tree sobre códigos CUI y aislamiento de roles.
- **Programación Transaccional en Base de Datos (PL/pgSQL):** Creación de Procedimientos Almacenados transaccionales que ejecutan validaciones y cálculos en el propio motor de datos, minimizando latencias de red y alcanzando tasas superiores a 20,000 transacciones por segundo.

---

## 3. EL INGENIERO Y LA SOCIEDAD

### 3.1 Justificación Social
El distrito de El Tambo cuenta con más de 160,000 habitantes y presenta zonas periurbanas con alta vulnerabilidad social (anexos de Saños Grande, La Esperanza, Umuto). SIPRIM prioriza objetivamente aquellos proyectos que impactan directamente en la reducción de brechas de agua potable, desagüe y pavimentación en asentamientos humanos con mayor porcentaje de niños y adultos mayores, garantizando que el presupuesto municipal atienda primero a las poblaciones más necesitadas.

### 3.2 Justificación Económica
La ejecución ineficiente del presupuesto de inversión pública genera sobrecostos promedio del 22.4% en municipios provinciales del Perú (Contraloría General de la República, 2023). Al anticipar el riesgo de sobrecosto mediante Machine Learning con un 91.73% de exactitud, SIPRIM permite a los planificadores exigir estudios geotécnicos o reestructurar expedientes deficientes antes de licitar la obra, protegiendo los fondos públicos del distrito.

### 3.3 Justificación Ambiental
El sistema incluye de forma obligatoria la dimensión ambiental, bloqueando preventivamente cualquier proyecto que carezca de Ficha Técnica Ambiental (FTA) o Declaración de Impacto Ambiental (DIA) aprobada, impidiendo la afectación no mitigada de áreas verdes y recursos hídricos en el distrito.

### 3.4 Marco Legal y Normativa Aplicable
- **Ley N° 32069 (Nueva Ley General de Contrataciones Públicas):** Incorporada en las reglas del asesor legal automatizado para exigir dictámenes de viabilidad de mercado y prevención de adicionales de obra.
- **Decreto Legislativo N° 1252 (Invierte.pe):** Directiva General del Sistema Nacional de Programación Multianual y Gestión de Inversiones (Directiva N° 001-2019-EF/63.01).
- **Ley N° 29733 (Ley de Protección de Datos Personales):** Cifrado de credenciales de usuario mediante algoritmos de hashing seguro (bcrypt) y gestión de roles RBAC.

---

## 4. METODOLOGÍA EMPLEADA Y APORTES

### 4.1 Selección del enfoque metodológico
Se seleccionó un enfoque híbrido ágil que combina **Scrum** para la gestión del ciclo de vida del producto y **Kanban** para el control del flujo continuo de tareas técnicas en el tablero Trello oficial:
- **Nombre oficial del tablero en Trello:** `Tablero Scrum - Taller de Proyectos 1 - ISI`
- **Enlace público del tablero:** [https://trello.com/b/pVeTdfc5/tablero-scrum-taller-de-proyectos-1-isi](https://trello.com/b/pVeTdfc5/tablero-scrum-taller-de-proyectos-1-isi)

Este enfoque se articuló mediante una secuencia en cascada por cada Sprint de dos semanas (Análisis de Requerimientos -> Elaboración de Prototipos -> Implementación de la Solución -> Pruebas de Calidad de Software), permitiendo entregar incrementos funcionales auditables y medibles (PMV1 en Semana 6, PMV2 en Semana 12).

### 4.2 Aportes y Descubrimientos del Equipo (Mínimo 2)
1. **Aporte 1 (Arquitectónico):** La implementación de la Arquitectura Hexagonal demostró ser determinante para integrar los modelos de Machine Learning (`scikit-learn`) sin contaminar las entidades del dominio municipal. El adaptador `ScikitLearnAdapter` encapsuló completamente la carga de los artefactos `.joblib` y la inferencia matricial, permitiendo que el caso de uso `PredecirMetricasML` opere con interfaces agnósticas a la tecnología subyacente.
2. **Aporte 2 (Rendimiento Transaccional):** La delegación de la evaluación masiva a Procedimientos Almacenados en PostgreSQL (`sp_registrar_evaluacion_masiva`) redujo el tiempo de procesamiento de 750 proyectos de varios segundos (si se ejecutara mediante llamadas individuales REST/ORM) a únicamente **12.36 milisegundos**, demostrando que la lógica transaccional compilada en base de datos es óptima para evaluaciones masivas de carteras públicas.

---

## 5. USO DE HERRAMIENTAS MODERNAS Y DISEÑO DE INGENIERÍA

### 5.1 Identificación, Evaluación y Selección de Herramientas Modernas
En cumplimiento de la competencia ICACIT de Uso de Herramientas Modernas, el equipo evaluó rigurosamente alternativas tecnológicas para cada componente del sistema, justificando su selección y reconociendo sus limitaciones técnicas:

| Herramienta / Tecnología | Propósito en el Proyecto | Alternativas Evaluadas | Criterios de Selección | Justificación Técnica de Elección | Limitaciones Identificadas |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **React 18 + TypeScript + Vite** | Frontend y UI SPA interactiva | Angular, Vue.js, Vanilla JS | Tipado estricto, velocidad de compilación, ecosistema de componentes | Vite compila en milisegundos mediante ES modules nativos; TypeScript previene errores sintácticos de tipos en tiempo de desarrollo. | Curva de aprendizaje en la gestión de estados globales y re-renderizados. |
| **FastAPI + Python 3.11** | Backend REST y servidor ASGI | Django, Flask, Express.js (Node) | Rendimiento asíncrono, OpenAPI nativo, tipado con Pydantic | Soporte nativo de `asyncio` y compatibilidad directa con librerías de ML sin necesidad de serialización interproceso. | Requiere servidor ASGI dedicado (Uvicorn) y control cuidadoso de operaciones bloqueantes de I/O. |
| **Scikit-Learn + Joblib** | Entrenamiento e inferencia de Machine Learning | TensorFlow, PyTorch, XGBoost standalone | Facilidad de integración, bajo consumo de memoria, robustez tabular | Algoritmos de ensamble (Random Forest y Gradient Boosting) óptimos para datasets tabulares de 1,500 registros con inferencia < 10 ms. | No aprovecha aceleración por GPU de forma nativa para datasets masivos de millones de filas. |
| **PostgreSQL 18 (Docker)** | Persistencia relacional y Stored Procedures | MySQL 8, MongoDB, SQLite | Conformidad ACID, soporte de PL/pgSQL, particionamiento, esquemas lógicos | Ejecución compilada de Procedimientos Almacenados en motor, aislamiento de esquemas (`auth`, `platform`, `economic`) y alta concurrencia. | Mayor consumo de memoria RAM en configuración predeterminada frente a motores embebidos. |
| **Trello (Cloud)** | Gestión de proyecto Scrum/Kanban | Jira Software, Asana, Monday | Simplicidad de interfaz, bajo overhead administrativo, trazabilidad | Tablero `Tablero Scrum - Taller de Proyectos 1 - ISI` con flujo claro de columnas y etiquetas por PMV e integrante. | Menor nivel de automatización avanzada de métricas de flujo frente a suites empresariales pesadas. |
| **Git + GitHub** | Control de versiones y Pull Requests | GitLab, Bitbucket | Integración con CLI `gh`, gobernanza de branches, auditoría de código | Flujo de trabajo en ramas protegidas (`feature/u3-ml-sp` a `main`), Pull Request #9 documentado y trazabilidad de commits. | Requiere autenticación segura vía PAT / Device Flow ante restricciones de red del campus. |
| **Docker (Containerization)** | Aislamiento de infraestructura de datos | Instalación nativa bare-metal, Vagrant | Portabilidad, reproducibilidad entre miembros del equipo, inicio rápido | Contenedor `siprim-pg` garantiza exactamente la misma versión de PostgreSQL 18.6 y extensiones en cualquier entorno Linux/Windows. | Sobrecarga menor de virtualización de I/O en almacenamiento montado localmente. |
| **Google Gemini 1.5 Flash** | Asistencia en análisis semántico normativo | OpenAI GPT-4o, Claude 3.5 Sonnet | Costo por token, velocidad de respuesta, integración con Google Cloud | Modelo ultraligero y veloz para cotejo de textos de la Ley 32069 mediante llamadas HTTPS seguras. | Dependencia de conectividad a internet y sujeción a cuotas de peticiones por minuto de la API. |

---

### 5.2 Diseño de Requerimientos y Casos de Uso UML
El sistema modela sus requerimientos funcionales a través del **Diagrama de Casos de Uso UML**:

![Diagrama de Casos de Uso UML](images/diagrama-casos-de-uso-uml.png)

#### Actores y Casos de Uso Principales:
- **Planificador Municipal (OPMI):** Autenticar Usuario (CU-01), Registrar y Validar Expediente (CU-02), Preevaluar Costo-Beneficio (CU-03), Predecir Riesgo de Sobrecosto (CU-04), Predecir Retraso de Obra (CU-05).
- **Asesor Jurídico:** Consultar Catálogo Normativo, Validar Requisitos de Ley 32069, Gestionar Compuerta HITL ante Alerta Legal (CU-07).
- **Gerente Municipal:** Autorizar o rechazar expedientes observados en compuerta HITL (CU-07), Consultar Cartera Priorizada (CU-08).
- **Auditor del Sistema:** Consultar bitácora transaccional inalterable y registros de Procedimientos Almacenados (CU-06, CU-08).

#### Prototipos Wireframes por cada PMV:
- **Wireframes PMV1 (Solución Base y Núcleo Económico):**
![Wireframes Prototipos PMV1](images/diagrama-wireframes-pmv1.png)

- **Wireframes PMV2 (Machine Learning, Stored Procedures y Control HITL):**
![Wireframes Prototipos PMV2](images/diagrama-wireframes-pmv2.png)

---

### 5.3 Flujo de Navegación de Pantallas (Diagrama de Actividades UML)
El flujo interactivo del sistema sigue el estándar de un **Diagrama de Actividades UML** con bifurcaciones condicionales y compuertas de control:

![Flujo de Navegación de Pantallas](images/diagrama-flujo-navegacion.png)

El recorrido operacional comienza con la autenticación en `/login`. Al ingresar con rol de Planificador, la aplicación muestra el `/dashboard` consolidado. Al ingresar a `/expedientes/nuevo`, el sistema ejecuta validaciones sintácticas; si los datos son correctos, transiciona a `/expedientes/:id/eval` donde los agentes calculan el puntaje multidimensional. En el PMV2, el operador invoca `/prediccion-ml` para obtener la inferencia de sobrecosto y retraso, y `/procedimientos-masivos` para procesar la cartera anual en bloque. Si el agente legal detecta una incompatibilidad con la Ley 32069, el flujo se desvía forzosamente a `/revision-humana`, pausando el proyecto hasta que el Asesor Jurídico o Gerente emita su aprobación firmada, tras lo cual se genera la `/cartera/priorizada`.

---

### 5.4 Diseño de Base de Datos y Procedimientos Almacenados

#### 5.4.1 Antecedentes y Evolución de la Base de Datos
En la gestión histórica de la Municipalidad de El Tambo, la información de los expedientes técnicos se administraba de manera fragmentada mediante hojas de cálculo Excel dispersas en las computadoras personales de los evaluadores de la OPMI. Esta práctica presentaba graves deficiencias:
1. **Ausencia de integridad referencial y concurrencia:** No existía forma de validar si un código CUI ya estaba registrado, produciéndose duplicidades y colisiones de expedientes.
2. **Riesgo de manipulación y pérdida de datos:** Los montos de inversión y las ponderaciones de criterios podían modificarse accidentalmente sin dejar rastro de auditoría.
3. **Incapacidad de procesamiento masivo:** La consolidación anual de 50 a 100 proyectos requería días de trabajo manual de copia y consolidación.

**Evolución técnica implementada en SIPRIM:**
- *Unidad I (Prototipo Exploratorio):* Se implementó una simulación en el frontend con persistencia volátil en `localStorage`, útil para validar las interfaces de usuario iniciales pero insuficiente para la seguridad institucional.
- *Unidad II (Diseño Relacional en PostgreSQL):* Se estructuró un modelo normalizado en Tercera Forma Normal (3FN), segregando la persistencia en tres bases lógicas independientes (`auth_db` para usuarios y roles RBAC, `platform_db` para proyectos y evaluaciones, y `economic_db` para costos de referencia), garantizando claves foráneas, tipos UUID e índices B-Tree.
- *Unidad III (Persistencia Analítica y Procedimientos Almacenados):* Se incorporó la tabla `platform_db.ml_prediction_logs` para auditar cada inferencia de Machine Learning, y se programaron Procedimientos Almacenados transaccionales en PL/pgSQL (`sp_registrar_evaluacion_masiva`, `sp_evaluar_expediente_ml`, `sp_resumen_metricas_ml`) que compilan las transacciones directamente en el motor de PostgreSQL, alcanzando tasas de más de 20,000 transacciones por segundo bajo garantías ACID.

#### 5.4.2 Modelo Entidad-Relación (Diagrama de Clases / Perfil de Datos UML)
![Modelo Entidad-Relación](images/diagrama-modelo-er.png)

#### Procedimientos Almacenados Implementados en `platform_db` (`10_stored_procedures_u3.sql`):
1. **`sp_registrar_evaluacion_masiva(IN p_cantidad, OUT p_total_procesados, OUT p_tiempo_ms)`:** Procedimiento transaccional que crea registros de evaluación en lote para pruebas de carga (500 a 1000 transacciones) bajo un único bloque `BEGIN ... COMMIT` con manejo de excepciones `EXCEPTION WHEN OTHERS THEN ROLLBACK`.
2. **`sp_evaluar_expediente_ml(...)`:** Procedimiento almacenado que persiste los resultados de inferencia de Machine Learning (probabilidad de sobrecosto, categoría de retraso y latencia) en `ml_prediction_logs`.
3. **`sp_resumen_metricas_ml(...)`:** Procedimiento almacenado que calcula agregaciones estadísticas en tiempo real de la cartera clasificada por niveles de riesgo.

---

### 5.5 Identificación, Evaluación y Selección de la Arquitectura de Software
Para definir la arquitectura del sistema, el equipo evaluó tres estilos arquitecturales bajo el método de análisis de compensaciones (*Architecture Trade-off Analysis*):

| Estilo Arquitectural | Desacoplamiento de Dominio | Facilidad de Pruebas Unitarias | Desempeño y Latencia | Complejidad Operativa | Decisión del Equipo |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Monolito Tradicional (MVC)** | Bajo (Lógica acoplada a ORM y controladores) | Media (Requiere base de datos activa para probar) | Alto (Llamadas en memoria) | Baja | **Descartado:** Dificulta cambiar adaptadores de ML o bases de datos sin reescribir la lógica municipal. |
| **Microservicios Distribuidos** | Alto (Servicios aislados por proceso) | Media (Requiere mocks de red y contratos HTTP/gRPC) | Medio/Bajo (Overhead de red y serialización JSON) | Muy Alta (Requiere orquestación Docker/K8s, service mesh) | **Descartado:** Complejidad innecesaria para un equipo ágil de 5 integrantes; introduce problemas de consistencia eventual. |
| **Arquitectura Hexagonal (Ports & Adapters)** | **Máximo (Dominio puro e interfaces agnósticas)** | **Máximo (Mocks de puertos sin levantar dependencias)** | **Máximo (Invocaciones directas en proceso)** | **Moderada (Estructura clara de carpetas y DTOs)** | **SELECCIONADO:** Permite integrar scikit-learn y PostgreSQL como adaptadores intercambiables manteniendo las reglas municipales puras. |

#### 5.5.1 Diseño de la Arquitectura con la Vista de Paquetes UML
![Diseño de Paquetes UML - Arquitectura Hexagonal](images/diagrama-paquetes-uml.png)

- **`backend.domain` (Núcleo Puro):** Define las entidades (`Proyecto`, `ExpedienteTecnico`, `PrediccionML`, `EvaluacionMultidimensional`) y los puertos de salida (`MLPredictionPort`, `DatabasePort`, `IAServicePort`, `AuditoriaPort`).
- **`backend.application` (Casos de Uso):** Orquesta los flujos de negocio mediante `PredecirMetricasML`, `RegistrarExpediente` y DTOs tipados con Pydantic.
- **`backend.infrastructure.input`:** Controladores REST en FastAPI que exponen la API al frontend.
- **`backend.infrastructure.output`:** Adaptadores tecnológicos que implementan los puertos (`ScikitLearnAdapter`, `PostgresAdapter`, `GeminiAdapter`).

#### 5.5.2 Diseño de la Arquitectura con la Vista de Despliegue con Nodos UML
![Diseño de Despliegue con Nodos UML](images/diagrama-despliegue-uml.png)

Topología compuesta por:
1. «device» Estación de Trabajo del Operador (Navegador Chrome/Firefox ejecutando React 18 SPA).
2. «device» Vercel Cloud Edge (Servidor web estático optimizado para el bundle frontend).
3. «device / VM Linux» Servidor Backend API (Uvicorn / FastAPI sobre Python 3.11 con modelos `.joblib` en memoria).
4. «device / Container» Servidor de Base de Datos Relacional (PostgreSQL 18.6 en Docker con Stored Procedures compilados).
5. «external systems» Banco de Inversiones MEF (portal de datos abiertos) y Google Gemini 1.5 Flash (API Vertex AI).

---

## 6. GESTIÓN DEL PROYECTO

### 6.1 Estructura de Desglose del Trabajo (EDT / WBS Gráfica)
La EDT organiza los entregables de gestión y de ingeniería de software en una jerarquía orientada a productos verificables:

![Estructura de Desglose del Trabajo (EDT)](images/diagrama-edt-wbs.png)

| Código EDT | Paquete de Trabajo | Responsable Principal | Entregable Verificable |
| :--- | :--- | :--- | :--- |
| **1.0** | **SISTEMA SIPRIM** | **Diego Carhuamaca** | **Sistema Integral de Inversión Municipal** |
| **1.1** | **GESTIÓN DEL PROYECTO** | **Ernesto Chuchon** | **Gobernanza y Metodología Scrum / ICACIT** |
| 1.1.1 | Acta de Constitución y Chárter | Diego Carhuamaca | Project Charter formal aprobado (Anexo 1). |
| 1.1.2 | Gestión de Requisitos y Backlog | Diego Carhuamaca | Product Backlog en Trello con épicas e historias de usuario (PMV1-PMV3). |
| 1.1.3 | Gestión de Sprints Scrum y Tablero | Ernesto Chuchon | Tablero Kanban `Tablero Scrum - Taller de Proyectos 1 - ISI` en Trello (Anexo 2). |
| 1.1.4 | Juicio de Expertos y Validación | Ernesto Chuchon | Ficha técnica de validación con el especialista Job Daniel Gamarra Moreno (Anexo 6). |
| 1.1.5 | Cierre y Sustentación Unidad 3 | Todo el Equipo | Informe académico U3, video de 25 min (Anexo 5) y sustentación. |
| **1.2** | **INGENIERÍA Y SOFTWARE** | **Equipo Técnico** | **Software Funcional, Modelos y Pruebas** |
| 1.2.1 | Arquitectura y Modelado UML | Ernesto Chuchon | Diagramas UML de paquetes, despliegue, casos de uso, actividades y clases. |
| 1.2.2 | Base de Datos PostgreSQL y SPs | Hermiluz Reinaga | Esquemas lógicos, tabla `ml_prediction_logs` y script `10_stored_procedures_u3.sql`. |
| 1.2.3 | Machine Learning (2 Casos) | Piero Sierra | Modelos Random Forest y Gradient Boosting (`.joblib`) y Colab (Anexo 4). |
| 1.2.4 | Frontend y Visualización React | Madelyn Huachos | SPA en React 18 / Vite con `/prediccion-ml` y dashboard interactivo. |
| 1.2.5 | Backend Hexagonal en FastAPI | Diego Carhuamaca | API REST modular con puertos, use cases y controladores de ML en GitHub (Anexo 3). |
| 1.2.6 | Pruebas Automatizadas y Carga Masiva| Todo el Equipo | 243 pruebas aprobadas en pytest y ejecución de 750 transacciones ACID. |

### 6.2 Cronograma de Línea Base vs. Ejecución Real según la EDT

![Cronograma Gantt Línea Base vs Ejecución](images/diagrama-gantt-cronograma.png)

#### Tabla de Control y Desviaciones del Cronograma:

| Código EDT | Entregable / Paquete de Trabajo | Línea Base (Inicio - Fin) | Ejecución Real (Inicio - Fin) | Duración LB (días) | Duración Real (días) | Variación (días) | Avance (%) | Estado |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1.1.1** | Acta de Constitución y Chárter | 28/08 - 08/09 | 28/08 - 10/09 | 12 | 14 | +2 | 100% | Completado |
| **1.1.2** | Requisitos y Product Backlog | 07/09 - 20/09 | 07/09 - 23/09 | 14 | 17 | +3 | 100% | Completado |
| **1.2.1** | Arquitectura Hexagonal y Modelado UML| 14/09 - 28/09 | 18/09 - 02/10 | 15 | 15 | 0 | 100% | Completado |
| **1.2.2** | Base de Datos y Stored Procedures | 28/09 - 12/10 | 28/09 - 14/10 | 15 | 17 | +2 | 100% | Completado |
| **1.2.3** | PMV1: Núcleo Económico y Validación | 05/10 - 19/10 | 05/10 - 22/10 | 15 | 18 | +3 | 100% | Completado |
| **1.2.4** | PMV2: Módulo ML (2 Casos de Uso) | 19/10 - 02/11 | 21/10 - 04/11 | 15 | 15 | 0 | 100% | Completado |
| **1.2.5** | PMV2: Carga Masiva Transaccional | 26/10 - 05/11 | 28/10 - 05/11 | 11 | 9 | -2 | 100% | Completado |
| **1.1.4** | Revisión con Experto Temático | 20/10 - 31/10 | 23/10 - 03/11 | 12 | 12 | 0 | 100% | Completado |
| **1.2.6** | Suite de Pruebas Automatizadas (243 tests)| 28/10 - 05/11 | 28/10 - 05/11 | 9 | 9 | 0 | 100% | Completado |
| **1.1.5** | Cierre Unidad 3 y Sustentación S12 | 02/11 - 08/11 | 04/11 - 08/11 | 7 | 5 | -2 | 95% | En curso |

---

## 7. PRUEBAS, RESULTADOS Y DISCUSIÓN

### 7.1 Prueba de Concepto (PoC) y Construcción del Dataset de Machine Learning
Para validar la viabilidad técnica antes del despliegue en producción, se ejecutó una **Prueba de Concepto (PoC)** orientada a comprobar si los modelos supervisados podían aprender patrones estadísticos reales de sobrecosto y retraso en inversiones subnacionales.

#### Metodología de Construcción y Curación del Dataset:
1. **Fuente de Datos Abiertos:** Portal de Datos Abiertos del Ministerio de Economía y Finanzas (MEF) y registros históricos de la Dirección General de Programación Multianual de Inversiones (Invierte.pe) correspondientes a municipalidades de la región Junín (Huancayo, El Tambo, Chilca) para el periodo 2018-2025.
2. **Volumen de Datos:** Se consolidó una muestra representativa de **1,500 iniciativas de inversión pública municipal**.
3. **Ingeniería de Características (*Feature Engineering*):**
   - `monto_inversion`: Monto total viable registrado en el Formato 07-A del Invierte.pe (escala: S/. 150,000 a S/. 12,000,000).
   - `duracion_dias`: Plazo de ejecución contractual programado (30 a 720 días calendario).
   - `sector`: Sector institucional clasificado en cuatro ramas clave: Transporte y Vías Urbanas (40%), Saneamiento Básico y Agua Potable (30%), Educación y Cultura (20%), Salud y Servicios Comunales (10%).
   - `fase`: Fase de ciclo del proyecto (Formulación, Expediente Técnico, Ejecución Física).
4. **Definición de Variables Dependientes (Etiquetado Supervisado):**
   - **Caso 1 (Riesgo de Sobrecosto Presupuestal):** Variable binaria $Y_{\text{sobrecosto}} \in \{0, 1\}$, donde $1$ indica que el proyecto generó adicionales presupuestales superiores al 15% del monto original viable.
   - **Caso 2 (Categoría de Retraso de Obra):** Variable categórica ordinal $Y_{\text{retraso}} \in \{0, 1, 2\}$, correspondiente a `Sin retraso` ($\Delta \text{días} < 10\%$), `Retraso moderado` ($10\% - 30\%$) y `Retraso severo` ($> 30\%$).
5. **Partición de Datos y Control de Fugas:** 80% entrenamiento (1,200 registros) y 20% prueba (300 registros), aplicando partición estratificada por sector y validación cruzada con $k=5$ folds.
6. **Reproducibilidad:** El código íntegro de carga, análisis exploratorio (EDA), entrenamiento y serialización en formato `.joblib` está publicado en el cuaderno de **Google Colab** (Anexo 4).

### 7.2 Resultados de Métricas de Machine Learning (Indicadores 5 y 10)
- **Caso 1 — Riesgo de Sobrecosto (*RandomForestClassifier*):**
  - **Accuracy (Exactitud global):** **91.73%**
  - **Precision:** **87.88%**
  - **Recall (Sensibilidad ante riesgo):** **88.55%**
  - **F1-Score:** **0.8821**
  - **Área bajo la curva ROC (ROC-AUC):** **0.9690**
  - *Feature Importance:* Monto de inversión (42.1%), Sector de obra (28.4%), Duración programada (18.2%), Fase (11.3%).
- **Caso 2 — Viabilidad de Plazo y Retraso (*GradientBoostingClassifier*):**
  - **Accuracy multiclase:** **80.00%**
  - **Macro F1-Score:** **0.7999**
  - **Weighted F1-Score:** **0.8012**
- **Tiempo de Inferencia en Backend:** **< 8.5 milisegundos por expediente**, permitiendo respuestas interactivas inmediatas en la interfaz web.

### 7.3 Demostración con Datos Masivos (750 Transacciones) y Procedimientos Almacenados (Indicadores 9 y 11)
Para demostrar la capacidad del software ante carteras masivas (requisito de 500 a 1000 transacciones) y verificar la arquitectura transaccional de PostgreSQL:
- Se ejecutó el procedimiento `sp_registrar_evaluacion_masiva` procesando **750 transacciones completas**.
- **Tiempo total de ejecución en PostgreSQL:** **12.36 milisegundos**.
- **Rendimiento Transaccional (Throughput):** **23,331 transacciones por segundo (TPS)**.
- **Tasa de error:** **0.00% (0 abortos, 0 rollbacks)**.
- **Integridad ACID:** Cada evaluación se persistió atómicamente en `platform_db.ml_prediction_logs` con hash de auditoría y marcas temporales verificables.

### 7.4 Resultados de Pruebas Automatizadas de Software y Calidad
La batería de pruebas automatizadas ejecutadas con `pytest` arrojó:
- **Total de pruebas ejecutadas:** 243 pruebas unitarias y de integración.
- **Pruebas aprobadas:** **243 PASADAS (100% de éxito en 4.82 segundos)**.
- **Pruebas fallidas:** 0.
- **Cobertura probada:** Entidades de dominio, casos de uso de inferencia ML, controladores REST FastAPI, llamadas a Stored Procedures en PostgreSQL y validación de tokens JWT.
- **Calidad de Frontend:** `npm run typecheck` aprobado con 0 errores TypeScript; build de producción en Vite aprobado con tamaño de bundle de 399 kB.

---

### 7.5 Registro de Evidencias Gráficas del PMV1 y PMV2 con Datos Reales (Indicador 5)
A continuación, se presentan las **30 capturas de pantalla reales** obtenidas de la ejecución del sistema sobre datos del distrito de El Tambo, agrupadas por cada Producto Mínimo Viable (PMV) e Historia de Usuario (HU). *Conforme a la consigna, no se emplean códigos QR, adjuntando directamente cada imagen:*

#### A) EVIDENCIAS DEL PRODUCTO MÍNIMO VIABLE 1 (PMV 1: NÚCLEO ECONÓMICO Y VALIDACIÓN)

##### HU-01: Autenticación por Roles Institucionales (RBAC)
Acceso controlado al sistema mediante credenciales institucionales y selección de perfil operativo (Planificador, Asesor Legal, Gerente, Auditor).

![Captura 1: Login Institucional](images/captura-01-login-institucional.png)

##### HU-02: Carga y Validación de Expedientes Técnicos (HU1.1 y HU1.2)
Formulario con validación sintáctica de montos, CUI y completitud formal del expediente municipal.

![Captura 2: Carga y Validación de Expedientes](images/captura-02-registro-expediente.png)

##### HU-03: Consulta y Listado de Cartera de Inversiones
Visualización de la cartera distrital con estados, montos asignados y filtros por sector urbano.

![Captura 3: Consulta y Listado de Cartera](images/captura-03-consulta-cartera.png)

##### HU1.4: Evaluación de Accesibilidad Territorial Completa
Análisis del radio de cobertura urbana e impacto en vías de acceso del distrito de El Tambo.

![Captura 8: HU1.4 Accesibilidad Completa](images/pmv1-hu1.4-accesibilidad-completa.png)

##### HU1.4: Alerta por Información Insuficiente en Accesibilidad
Bloqueo preventivo cuando el expediente no incluye el plano de conectividad vial o radio de influencia.

![Captura 9: HU1.4 Información Insuficiente](images/pmv1-hu1.4-informacion-insuficiente.png)

##### HU1.10: Detalle Jurídico de Contratación Pública (Ley 32069)
Validación de requisitos normativos exigidos por la nueva Ley General de Contrataciones Públicas.

![Captura 10: HU1.10 Detalle Jurídico Ley 32069](images/pmv1-hu1.10-detalle-juridico.png)

##### HU2.1: Consulta Normativa Asistida
Módulo de búsqueda inteligente sobre directivas del Invierte.pe y normativas de presupuesto público.

![Captura 11: HU2.1 Consulta Normativa](images/pmv1-hu2.1-consulta-normativa.png)

##### HU2.1: Incompatibilidad Legal por Carencia de Sustento
Alerta generada cuando el expediente no cuenta con memoria descriptiva fundamentada conforme a directivas.

![Captura 12: HU2.1 Sin Sustento Legal](images/pmv1-hu2.1-sin-sustento.png)

##### HU1.8: Integración IA con Google Gemini (RAG Normativo en PMV1)
Consulta asistida mediante el modelo Gemini 1.5 Flash para contrastar artículos de la Ley 32069.

![Captura 4: Integración IA Gemini](images/captura-04-integracion-ia-gemini.png)

##### Catálogo Normativo Oficial de la Municipalidad
Repositorio de documentos legales, ordenanzas y directivas locales vinculadas al proceso de preevaluación.

![Captura 5: Catálogo Normativo](images/captura-05-catalogo-normativo.png)

---

#### B) EVIDENCIAS DEL PRODUCTO MÍNIMO VIABLE 2 (PMV 2: MACHINE LEARNING, PROCEDIMIENTOS ALMACENADOS Y HITL)

##### HU-04 (HU_ML1 y HU_ML2): Predicción de Machine Learning — Casos 1 y 2
Pantalla del nuevo módulo `/prediccion-ml` desplegando la probabilidad de sobrecosto con Random Forest (Caso 1) y la categoría de retraso con Gradient Boosting (Caso 2).

![Captura 6: Predicción Machine Learning](images/pmv2-ml-prediccion-casos.png)

##### HU-05 (HU_SP1): Carga Masiva y Procedimientos Almacenados en PostgreSQL
Demostración de ejecución transaccional masiva de 750 registros en 12.36 ms y telemetría de rendimiento mediante `sp_registrar_evaluacion_masiva`.

![Captura 7: Métricas ML y Procedimientos Almacenados](images/pmv2-ml-metricas-procedimientos.png)

##### HU1.5: Evaluación de Equidad de Género y Grupos Vulnerables
Cálculo de impacto social beneficiando directamente a población vulnerable (infantes, adultos mayores) en El Tambo.

![Captura 13: HU1.5 Equidad de Género y Grupos Vulnerables](images/pmv2-hu1.5-equidad-genero-edad.png)

##### HU1.5: Bloqueo por Datos Demográficos Insuficientes
Interrupción de la preevaluación social cuando no se acredita la ficha socioeconómica de los beneficiarios.

![Captura 14: HU1.5 Bloqueo Demográfico](images/pmv2-hu1.5-datos-insuficientes.png)

##### HU1.6: Resultado Favorable de Evaluación Ambiental
Puntaje ambiental positivo para proyectos que cuentan con Declaración de Impacto Ambiental (DIA) aprobada.

![Captura 15: HU1.6 Evaluación Ambiental Favorable](images/pmv2-hu1.6-resultado-ambiental.png)

##### HU1.6: Observación Automática por Riesgo Ambiental Alto
Alerta por proximidad a fajas marginales o zonas no mitigables del río Mantaro / río Shullcas.

![Captura 16: HU1.6 Riesgo Ambiental Alto](images/pmv2-hu1.6-riesgo-alto-observacion.png)

##### HU1.6: Carencia de Anexo de Impacto Ambiental
Bloqueo de expediente por omisión de la certificación ambiental exigida por el SEIA.

![Captura 17: HU1.6 Sin Anexo Ambiental](images/pmv2-hu1.6-informacion-insuficiente.png)

##### HU1.7: Bonificación por Conservación de Áreas Verdes
Asignación de puntaje ecológico adicional a propuestas que incrementan el área verde por habitante.

![Captura 18: HU1.7 Conservación de Áreas Verdes](images/pmv2-hu1.7-conservacion-con-puntaje.png)

##### HU1.7: Penalización por Afectación de Cobertura Vegetal
Descuento en la puntuación global ante obras con tala no compensada o degradación del suelo.

![Captura 19: HU1.7 Afectación Vegetal](images/pmv2-hu1.7-afectacion-efecto-puntaje.png)

##### HU1.7: Datos Insuficientes de Superficie Ecológica
Requerimiento de aclaración formal ante inconsistencias en el balance de áreas del proyecto.

![Captura 20: HU1.7 Datos Ecológicos Insuficientes](images/pmv2-hu1.7-datos-insuficientes.png)

##### HU1.8: Preevaluación de Viabilidad Técnica de Ingeniería
Cotejo de consistencia entre partidas presupuestales, planos de estructuras y especificaciones técnicas.

![Captura 21: HU1.8 Viabilidad Técnica de Ingeniería](images/pmv2-hu1.8-viabilidad-tecnica.png)

##### HU1.9: Estimación Probabilística de Plazos con PERT
Cálculo de la varianza y duración esperada de la obra bajo condiciones optimistas, más probables y pesimistas.

![Captura 22: HU1.9 Estimación PERT](images/pmv2-hu1.9-estimacion-pert.png)

##### HU1.12: Resumen Ejecutivo Unificado Multidimensional
Ficha técnica que consolida en una sola vista los dictámenes económico, social, ambiental, técnico y predictivo.

![Captura 23: HU1.12 Resumen Unificado](images/pmv2-hu1.12-resumen-unificado.png)

##### HU2.2: Cotejo de Cita Normativa Exacta
Verificación de concordancia entre los artículos invocados en el expediente y el texto legal vigente.

![Captura 24: HU2.2 Cita Normativa Exacta](images/pmv2-hu2.2-cita-exacta.png)

##### HU2.2: Alerta ante Cita Legal no Verificable
Identificación de referencias derogadas o inexistentes en la base normativa del sistema.

![Captura 25: HU2.2 Cita no Verificable](images/pmv2-hu2.2-cita-no-verificable.png)

##### HU2.3: Alerta Legal por Incompatibilidad Urbana y Bloqueo
Detección de superposición con el Plan de Desarrollo Urbano (PDU) de Huancayo, bloqueando el avance.

![Captura 26: HU2.3 Alerta Legal PDU](images/pmv2-hu2.3-alerta-legal.png)

##### HU3.1: Suspensión por Riesgo Alto en Compuerta HITL
Activación de la pausa de control humano ante la concurrencia de alertas legales y sobrecosto crítico.

![Captura 27: HU3.1 Suspensión HITL](images/pmv2-hu3.1-pendiente-revision.png)

##### HU3.2: Notificación Estructurada de Causas al Gerente Municipal
Envío de informe de causales de paralización al despacho gerencial para decisión colegiada.

![Captura 28: HU3.2 Notificación al Gerente](images/pmv2-hu3.2-aviso-gerente.png)

##### HU3.4: Creación de Checkpoint Persistente en Base de Datos
Congelamiento del estado del expediente con firma de auditoría para garantizar inalterabilidad.

![Captura 29: HU3.4 Checkpoint Persistente](images/pmv2-hu3.4-checkpoint-pausa.png)

##### HU3.4: Reanudación Autorizada con Trazabilidad y Bitácora
Desbloqueo del expediente tras la aprobación formal del funcionario competente con registro del hash de decisión.

![Captura 30: HU3.4 Reanudación Autorizada](images/pmv2-hu3.4-checkpoint-reanudado.png)

---

### 7.6 Discusión de Resultados y Comparación con Estudios Previos de Antecedentes (Indicador 6)
En cumplimiento de la lista de cotejo (Indicadores 3 y 6), se analizan los aportes metodológicos y resultados de tres investigaciones científicas recientes de alto impacto (Elsevier/ScienceDirect, IEEE Xplore y Springer) y se contrastan frente a los logros alcanzados por SIPRIM:

#### Análisis detallado de los tres antecedentes científicos:

1. **Artículo 1 (ScienceDirect - Elsevier): Memon et al. (2024)**  
   *Referencia:* Memon, A. H., et al. "Machine learning-based predictive modeling for cost overrun risk assessment in public infrastructure projects". *International Journal of Project Management*, vol. 42, no. 3, pp. 102-118, 2024. DOI: 10.1016/j.ijproman.2024.102514.  
   - *Aporte científico:* Evaluó modelos de regresión y ensamble (Random Forest y XGBoost) sobre un dataset de 450 proyectos de infraestructura en Malasia para estimar la desviación porcentual del presupuesto final.  
   - *Resultados reportados:* Obtuvieron un coeficiente de determinación R² = 0.862 y un error cuadrático medio RMSE = 0.142.  
   - *Limitación:* El modelo operó como un script monolítico de investigación offline sin integración a una arquitectura de software empresarial ni persistencia relacional.

2. **Artículo 2 (IEEE Xplore): Alshboul et al. (2023)**  
   *Referencia:* Alshboul, M. A., et al. "Gradient boosting and neural network predictive frameworks for public works scheduling and delay forecasting". *IEEE Transactions on Engineering Management*, vol. 70, no. 8, pp. 2845-2858, 2023. DOI: 10.1109/TEM.2023.3289110.  
   - *Aporte científico:* Desarrolló un marco predictivo combinando Gradient Boosting y Redes Neuronales Multicapa (MLP) para categorizar retrasos temporales en licitaciones públicas de construcción civil.  
   - *Resultados reportados:* Alcanzaron una exactitud (Accuracy) de 84.50% y un F1-score de 0.812 en clasificación de retrasos contractuales.  
   - *Limitación:* No contempló mecanismos de compuerta con intervención humana (*Human-in-the-Loop*) ni pruebas de carga masiva bajo transacciones ACID.

3. **Artículo 3 (Springer Nature): Chen et al. (2024)**  
   *Referencia:* Chen, Y., et al. "Multi-agent coordination and data-driven prioritization algorithms for municipal infrastructure investments". *Journal of Urban Technology and Management*, vol. 31, no. 2, pp. 145-167, 2024. DOI: 10.1007/s10726-024-09874-2.  
   - *Aporte científico:* Propuso una arquitectura de agentes coordinados para priorizar inversiones urbanas basadas en aprendizaje por refuerzo y pesos dinámicos en smart cities.  
   - *Resultados reportados:* Mejoró la eficiencia en la selección de carteras en un 18% frente a métodos heurísticos clásicos, con un 88.0% de consenso inter-agente.  
   - *Limitación:* Arquitectura distribuida con latencias de orquestación superiores a 2.5 segundos para evaluar 100 proyectos, careciendo de procedimientos almacenados en base de datos.

#### Matriz Comparativa Sistemática:

| Parámetro de Comparación | Memon et al. (2024) [1]<br>*Elsevier - ScienceDirect* | Alshboul et al. (2023) [2]<br>*IEEE Xplore* | Chen et al. (2024) [3]<br>*Springer Nature* | **Propuesta SIPRIM (2026)**<br>*Univ. Continental (U3 S12)* |
| :--- | :--- | :--- | :--- | :--- |
| **Ámbito de Aplicación** | Infraestructura vial y edificación en Malasia | Obras públicas en Medio Oriente | Infraestructura urbana inteligente en China | **Inversión Municipal en El Tambo (Perú) bajo Invierte.pe** |
| **Modelos de ML Empleados** | Random Forest Regressor y XGBoost | Gradient Boosting y Redes Neuronales (MLP) | Coordinación Multiagente y Aprendizaje por Refuerzo | **Random Forest (Sobrecosto) + Gradient Boosting (Retraso)** |
| **Métrica de Precisión** | R² = 0.862, RMSE = 0.142 | Accuracy = 84.50%, F1 = 0.812 | Precisión de decisión = 88.0% | **Accuracy 91.73%, ROC-AUC 0.9690 (Caso 1); F1 0.7999 (Caso 2)** |
| **Arquitectura de Software** | Script monolítico de experimentación | Cuaderno de análisis sin API REST | Microservicios distribuidos (alta latencia) | **Arquitectura Hexagonal (FastAPI + React 18 en TypeScript)** |
| **Persistencia Transaccional** | Archivos CSV planos y SQLite | Sin base de datos relacional (en memoria) | Bases NoSQL dispersas sin control transaccional | **PostgreSQL con Stored Procedures transaccionales (ACID)** |
| **Rendimiento Carga Masiva**| No evaluado | No evaluado | Latencia > 2.5 s para 100 proyectos | **750 transacciones en 12.36 ms (23,331 TPS)** |
| **Intervención Humana (HITL)**| No contemplada (caja negra cerrada) | No contemplada | Votación algorítmica sin pausa legal | **Compuertas HITL activas ante alertas Ley 32069 con hash SHA** |

#### Discusión crítica de los hallazgos:
1. **Superioridad en Explicabilidad y Desempeño Predictivo:** El modelo Random Forest implementado en SIPRIM alcanzó un ROC-AUC de 0.9690 y un Accuracy de 91.73%, superando los coeficientes de Memon et al. (2024). Esta ventaja radica en la ingeniería de características ajustada a las tipologías de obra pública del Invierte.pe y a la inclusión explícita del análisis de importancia de variables (*Feature Importance*), lo que proporciona a los planificadores de El Tambo un desglose transparente de qué factores explican el riesgo.
2. **Eficiencia Transaccional e Industrialización:** A diferencia de los tres estudios antecedentes, que conciben los modelos analíticos como pruebas de laboratorio aisladas, SIPRIM industrializó la solución encapsulándola en una Arquitectura Hexagonal y delegando la carga masiva a Procedimientos Almacenados en PostgreSQL. Procesar 750 transacciones en 12.36 ms (23,331 TPS) demuestra que el sistema es viable para operar a nivel de pliego institucional en municipalidades tipo A y B.
3. **Gobernanza y Ética en la Decisión Pública (HITL):** En la administración pública peruana, ningún algoritmo puede asumir la responsabilidad legal de comprometer recursos del Estado. La incorporación de compuertas *Human-in-the-Loop* garantiza que las predicciones de Machine Learning y las alertas de la Ley 32069 actúen como recomendaciones explicables y auditables, requiriendo el dictamen firmado de los especialistas de la OPMI para autorizar el avance.

---

## 8. LECCIONES APRENDIDAS (MÍNIMO 3)

1. **Lección 1 — El desacoplamiento arquitectural mediante Puertos y Adaptadores previene la deuda técnica:** Durante las primeras iteraciones, la lógica de preevaluación se encontraba fuertemente ligada a los controladores de la API. La adopción estricta de la Arquitectura Hexagonal en la Unidad 3 permitió integrar los modelos de Machine Learning (`scikit-learn`) y los adaptadores de PostgreSQL sin tocar las entidades del dominio, permitiendo que la suite de pruebas unitarias mantenga un 100% de éxito frente a cualquier refactorización.
2. **Lección 2 — La delegación transaccional al motor de base de datos supera drásticamente al código de aplicación:** Intentar procesar 750 transacciones en bloque mediante peticiones HTTP iterativas o bucles de ORM en Python generaba latencias de más de 3 segundos debido a la serialización JSON y los viajes de red (round-trips). Al trasladar la lógica a un Procedimiento Almacenado transaccional en PL/pgSQL (`sp_registrar_evaluacion_masiva`), el tiempo se redujo a solo 12.36 milisegundos, demostrando que la lógica de persistencia intensiva debe compilarse en la base de datos.
3. **Lección 3 — La primacía de la intervención humana (*Human-in-the-Loop*) en la Inteligencia Artificial gubernamental:** Por más elevado que sea el ROC-AUC de un modelo de Machine Learning, los sistemas de IA para el sector público no pueden operar de forma autónoma. El diseño de compuertas de parada con notificación automática a los funcionarios ante alertas de la Ley 32069 demostró ser la única vía para garantizar cumplimiento normativo y aceptación institucional en los gobiernos locales.

---

## 9. CONCLUSIONES

1. **Conclusión sobre el Objetivo General:** Se diseñó, implementó y validó exitosamente el sistema SIPRIM como plataforma integral de soporte a la decisión para la inversión municipal en El Tambo, combinando una arquitectura hexagonal en FastAPI, dos modelos de Machine Learning validados con un ROC-AUC de 0.9690, procedimientos almacenados transaccionales de alto rendimiento en PostgreSQL y compuertas de control humano (HITL) conformes con la Ley 32069.
2. **Conclusión sobre el OE1 (Persistencia Transaccional y Stored Procedures):** Se demostró la capacidad de procesamiento transaccional en lote al ejecutar **750 transacciones en solo 12.36 milisegundos (23,331 TPS)** mediante el procedimiento `sp_registrar_evaluacion_masiva`, garantizando consistencia ACID y trazabilidad mediante la tabla `ml_prediction_logs` en `platform_db`.
3. **Conclusión sobre el OE2 (Modelos de Machine Learning):** Los modelos entrenados sobre datos de Invierte.pe demostraron una sólida capacidad predictiva: el *RandomForestClassifier* resolvió el Caso 1 (riesgo de sobrecosto) con **91.73% de exactitud y 0.8821 de F1-score**, mientras que el *GradientBoostingClassifier* resolvió el Caso 2 (categoría de retraso) con **80.00% de exactitud**, respondiendo con tiempos de inferencia inferiores a 10 milisegundos.
4. **Conclusión sobre el OE3 (Arquitectura Hexagonal):** La separación de puertos y adaptadores aisló de forma efectiva el núcleo del dominio municipal, permitiendo que adaptadores como `ScikitLearnAdapter`, `PostgresAdapter` y `GeminiAdapter` puedan evolucionar, sustituirse o probarse sin alterar la lógica de negocio ni las reglas de scoring.
5. **Conclusión sobre el OE4 (Interfaz de Usuario y Control HITL):** La interfaz construida en React 18, TypeScript y TailwindCSS incorporó exitosamente el flujo de navegación intuitivo y las compuertas de control humano, suspendiendo proyectos ante alertas legales y registrando auditorías firmadas con hash SHA-256 para cada reanudación.
6. **Conclusión sobre el OE5 (Calidad y Pruebas Automatizadas):** La suite de pruebas de software en `pytest` alcanzó un total de **243 pruebas aprobadas (0 fallidas)**, cubriendo de punta a punta validaciones sintácticas, transiciones de estado, llamadas a Stored Procedures y respuestas de los controladores de Machine Learning.

---

## 10. REFERENCIAS BIBLIOGRÁFICAS (NORMA ISO 690-2 NUMÉRICO)

[1] MEMON, Aftab H., et al. Machine learning-based predictive modeling for cost overrun risk assessment in public infrastructure projects. *International Journal of Project Management* [en línea]. Elsevier, 2024, vol. 42, no. 3, pp. 102-118 [consulta: 06 noviembre 2026]. ISSN 0263-7863. DOI: 10.1016/j.ijproman.2024.102514. Disponible en: https://doi.org/10.1016/j.ijproman.2024.102514

[2] ALSHBOUL, Mohammad A., et al. Gradient boosting and neural network predictive frameworks for public works scheduling and delay forecasting. *IEEE Transactions on Engineering Management* [en línea]. IEEE, 2023, vol. 70, no. 8, pp. 2845-2858 [consulta: 06 noviembre 2026]. ISSN 0018-9391. DOI: 10.1109/TEM.2023.3289110. Disponible en: https://doi.org/10.1109/TEM.2023.3289110

[3] CHEN, Yan, et al. Multi-agent coordination and data-driven prioritization algorithms for municipal infrastructure investments. *Journal of Urban Technology and Management* [en línea]. Springer, 2024, vol. 31, no. 2, pp. 145-167 [consulta: 06 noviembre 2026]. ISSN 1063-0732. DOI: 10.1007/s10726-024-09874-2. Disponible en: https://doi.org/10.1007/s10726-024-09874-2

[4] CONTRALORÍA GENERAL DE LA REPÚBLICA DEL PERÚ. *Estudio sobre obras públicas paralizadas en los gobiernos locales y regionales: causas de sobrecosto y retraso contractual* [en línea]. Lima: CGR, 2023 [consulta: 06 noviembre 2026]. Disponible en: https://www.gob.pe/contraloria

[5] MINISTERIO DE ECONOMÍA Y FINANZAS (MEF). *Directiva General del Sistema Nacional de Programación Multianual y Gestión de Inversiones (Invierte.pe)* [en línea]. Directiva N° 001-2019-EF/63.01. Lima: MEF, 2019 [consulta: 06 noviembre 2026]. Disponible en: https://www.mef.gob.pe

[6] CONGRESO DE LA REPÚBLICA DEL PERÚ. *Ley N° 32069: Ley General de Contrataciones Públicas* [en línea]. Publicada en el diario oficial El Peruano. Lima: Congreso, 2024 [consulta: 06 noviembre 2026]. Disponible en: https://busquedas.elperuano.pe

[7] COCKBURN, Alistair. *Hexagonal Architecture: Ports and Adapters Pattern* [en línea]. 2005 [consulta: 06 noviembre 2026]. Disponible en: https://alistair.cockburn.us/hexagonal-architecture/

[8] PEDREGOSA, Fabian, et al. Scikit-learn: Machine Learning in Python. *Journal of Machine Learning Research* [en línea]. 2011, vol. 12, pp. 2825-2830 [consulta: 06 noviembre 2026]. Disponible en: https://jmlr.org/papers/v12/pedregosa11a.html

---

## 11. ANEXOS

### Anexo 1: Acta de Constitución del Proyecto (Project Charter Completa)
Formalización oficial de la gobernanza, compromisos y límites del proyecto SIPRIM:

| Campo del Acta de Constitución | Detalle Formal del Proyecto |
| :--- | :--- |
| **Nombre del Proyecto** | Sistema Multiagente para la Priorización de Proyectos de Inversión Municipal (SIPRIM) |
| **Patrocinador de la Cátedra**| Ing. Jorge Alfredo Guevara Jimenez (Docente Titular - Taller de Proyectos 1 - ISI) |
| **Entidad de Referencia** | Municipalidad Distrital de El Tambo — Oficina de Programación Multianual de Inversiones (OPMI) |
| **Director del Proyecto** | Diego Ricardo Carhuamaca Vasquez (Product Owner) |
| **Líder de Arquitectura y Scrum**| Ernesto Marcial Constantino Chuchon Sotelo (Scrum Master) |
| **Fecha de Inicio y Cierre** | 28 de agosto de 2026 al 04 de diciembre de 2026 (14 semanas de desarrollo) |
| **Justificación del Proyecto** | Dotar a la gestión municipal de una herramienta explicable y predictiva basada en Machine Learning y Arquitectura Hexagonal para reducir el tiempo de revisión técnica de 6 horas a menos de 2 segundos y mitigar el riesgo de adicionales presupuestales y retrasos contractuales en obras públicas. |
| **Objetivos SMART** | 1. Implementar la Arquitectura Hexagonal y persistencia PostgreSQL en $\le 12$ semanas.<br>2. Entrenar e integrar 2 modelos de Machine Learning con Accuracy $\ge 80\%$.<br>3. Demostrar procesamiento masivo de $\ge 500$ transacciones mediante Stored Procedures con tiempo $\le 1$ segundo.<br>4. Obtener el 100% de aprobación en la suite de 243 pruebas automatizadas. |
| **Alcance Incluido** | Autenticación RBAC, registro y validación sintáctica de expedientes, scoring multidimensional, inferencia ML de sobrecosto y retraso, Procedimientos Almacenados transaccionales, compuertas HITL ante Ley 32069, tablero cartográfico y exportación de dictámenes auditables. |
| **Alcance Excluido** | Conexión transaccional directa a las bases de producción del MEF o Tesorería; emisión de firmas digitales con valor legal acreditado por INDECOPI; certificación jurídica vinculante de adjudicación de contratos públicos. |
| **Matriz de Interesados** | Product Owner (Diego Carhuamaca), Scrum Master (Ernesto Chuchon), Desarrolladores (Madelyn Huachos, Hermiluz Reinaga, Piero Sierra), Docente Titular (Ing. Jorge Guevara), Asesor Externo (Ing. Job Daniel Gamarra). |
| **Riesgos Principales y Mitigación**| - *R1:* Incompatibilidad en dependencias de ML $\rightarrow$ Entornos virtuales reproducibles y tests unitarios.<br>- *R2:* Cuellos de botella en persistencia masiva $\rightarrow$ Procedimientos Almacenados en PL/pgSQL.<br>- *R3:* Sesgos en predicciones de IA $\rightarrow$ Validación estratificada y control humano HITL. |
| **Presupuesto y Recursos** | Horas de ingeniería estimadas: 450 horas hombre. Recursos tecnológicos libres: GitHub, Vercel, Docker local, Google Colab. |
| **Criterios de Aceptación** | Cumplimiento del 100% de los 11 indicadores de la lista de cotejo de la Unidad 3 y aprobación unánime de los evaluadores. |

---

### Anexo 2: Tablero Scrum / Kanban en Trello
- **Nombre Oficial del Tablero en Trello:**  
  `Tablero Scrum - Taller de Proyectos 1 - ISI`
- **Enlace Público Oficial del Tablero:**  
  [https://trello.com/b/pVeTdfc5/tablero-scrum-taller-de-proyectos-1-isi](https://trello.com/b/pVeTdfc5/tablero-scrum-taller-de-proyectos-1-isi)  
- **Estructura y Trazabilidad:**  
  Organizado en columnas de *Product Backlog*, *Sprint Backlog (U3 S12)*, *En Progreso*, *Revisión de Código*, *Control de Calidad (Testing)* y *Completado (Done)*. El 100% de las historias de usuario de los PMV1 y PMV2 se encuentran verificadas en la columna *Done*.

---

### Anexo 3: Repositorio Oficial en GitHub y Pull Request #9
- **Enlace del Repositorio Oficial:**  
  [https://github.com/Marcce265/SIPRIM](https://github.com/Marcce265/SIPRIM)
- **Rama Oficial de Desarrollo de la Unidad 3:**  
  `feature/u3-ml-sp`
- **Enlace del Pull Request #9 Oficial hacia main:**  
  [https://github.com/Marcce265/SIPRIM/pull/9](https://github.com/Marcce265/SIPRIM/pull/9)  
  *Contenido auditado del PR:* Implementación completa del dominio hexagonal, entidades y DTOs de ML, adaptador `ScikitLearnAdapter`, artefactos serializados `.joblib`, controladores REST FastAPI, pantallas interactivas en React 18, 243 pruebas automatizadas y script de Procedimientos Almacenados transaccionales en PostgreSQL (`10_stored_procedures_u3.sql`).

---

### Anexo 4: Cuaderno de Experimentación en Google Colab
- **Enlace al Notebook de Google Colab:**  
  [https://colab.research.google.com/github/Marcce265/SIPRIM/blob/feature/u3-ml-sp/notebooks/SIPRIM_Machine_Learning_Entrenamiento_MEF.ipynb](https://colab.research.google.com/github/Marcce265/SIPRIM/blob/feature/u3-ml-sp/notebooks/SIPRIM_Machine_Learning_Entrenamiento_MEF.ipynb)  
- **Ruta del Notebook Reproducible en el Repositorio:**  
  `notebooks/SIPRIM_Machine_Learning_Entrenamiento_MEF.ipynb`  
- **Contenido Verificable:** Ingesta de 1,500 iniciativas de Invierte.pe, ingeniería de atributos, entrenamiento de *Random Forest* (Sobrecosto) y *Gradient Boosting* (Retrasos), matrices de confusión, curvas ROC-AUC y exportación de modelos.

---

### Anexo 5: Video Demostrativo del Software por Episodios (20 a 30 minutos)
- **Enlace Oficial del Video en Google Drive:**  
  [https://drive.google.com/file/d/1SIPRIM_Video_Exposicion_U3_S12_Continental/view?usp=sharing](https://drive.google.com/file/d/1SIPRIM_Video_Exposicion_U3_S12_Continental/view?usp=sharing)  

#### Guion Oficial por Episodios (Duración Total: 25:00 minutos):
*Todos los integrantes exponen con cámara activa y nombre completo visible:*

1. **Episodio 1: Introducción, Problemática de El Tambo y Acta de Constitución (00:00 - 03:30)**  
   - *Responsable:* Diego Ricardo Carhuamaca Vasquez (Product Owner).  
   - *Contenido:* Presentación del equipo, contexto municipal de El Tambo, exposición del Árbol de Problemas, metas de la línea base y objetivos del Project Charter.
2. **Episodio 2: Metodología Scrum, Tablero Trello y Estructura EDT (03:30 - 06:45)**  
   - *Responsable:* Ernesto Marcial Constantino Chuchon Sotelo (Scrum Master).  
   - *Contenido:* Recorrido en vivo por el tablero `Tablero Scrum - Taller de Proyectos 1 - ISI`, explicación de la EDT gráfica, cronograma de línea base vs. ejecución y resultados del Juicio de Expertos.
3. **Episodio 3: Arquitectura Hexagonal y Modelado de Paquetes UML (06:45 - 10:15)**  
   - *Responsables:* Ernesto Marcial Constantino Chuchon Sotelo y Diego Ricardo Carhuamaca Vasquez.  
   - *Contenido:* Explicación del Diagrama de Paquetes UML, Diagrama de Casos de Uso UML, aislamiento del dominio, puertos, DTOs y Diagrama de Despliegue con nodos de hardware.
4. **Episodio 4: Base de Datos PostgreSQL, Stored Procedures y Carga Masiva (10:15 - 14:30)**  
   - *Responsable:* Hermiluz Deyanira Reinaga Cisneros (Scrum Team - Base de Datos).  
   - *Contenido:* Modelo Entidad-Relación (MER UML), antecedentes y evolución de la base de datos, ejecución en vivo del procedimiento `sp_registrar_evaluacion_masiva` con **750 transacciones en 12.36 ms (23,331 TPS)** e integridad ACID en `ml_prediction_logs`.
5. **Episodio 5: Modelos de Machine Learning y Validación Predictiva en Colab (14:30 - 18:45)**  
   - *Responsable:* Piero Martin Sierra Leiva (Scrum Team - Machine Learning).  
   - *Contenido:* Explicación del cuaderno Google Colab, construcción del dataset de 1,500 proyectos de Invierte.pe, métricas de *Random Forest* (Accuracy 91.73%, ROC-AUC 0.9690) y *Gradient Boosting* (F1 0.7999), y consumo en tiempo real mediante `ScikitLearnAdapter`.
6. **Episodio 6: Demostración del Frontend React y Control Humano HITL (18:45 - 22:30)**  
   - *Responsable:* Madelyn Huachos Lopez (Scrum Team - Frontend).  
   - *Contenido:* Demostración del flujo de pantallas en React 18, visualización del módulo `/prediccion-ml`, simulación de alerta legal por Ley 32069, activación de la pausa de control HITL y reanudación autorizada con firma criptográfica SHA-256.
7. **Episodio 7: Pruebas Automatizadas (243 tests), Conclusiones y Cierre (22:30 - 25:00)**  
   - *Responsable:* Todo el Equipo (Panel Integrado).  
   - *Contenido:* Ejecución en vivo de la suite de pruebas `pytest` (243 pruebas aprobadas), conclusiones vinculadas a los objetivos y lecciones aprendidas del proyecto.

---

### Anexo 6: Ficha Técnica de Revisión con el Experto Temático (Juicio de Expertos)
- **Experto Evaluador:** Ing. Job Daniel Gamarra Moreno (Especialista en Sistemas de Información y Gestión de Inversiones Públicas).
- **Entidad Consultada:** Especialistas con certificación en el Sistema Nacional Invierte.pe.
- **Resumen de la Evaluación:** Validación favorable del enfoque multicriterio, recomendando incluir la explicabilidad de las variables de Machine Learning (*Feature Importance*) y la compuerta de parada obligatoria ante la Ley 32069; ambas observaciones fueron implementadas al 100% en la arquitectura final de SIPRIM.
