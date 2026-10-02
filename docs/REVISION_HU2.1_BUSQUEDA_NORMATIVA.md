# Revisión e implementación de HU2.1

Fecha de revisión: 2026-10-01.

## Historia heredada

Como Asesor Jurídico, quiero que el sistema busque automáticamente en las
normativas vigentes para no revisar manualmente cientos de páginas.

## Correspondencia con la documentación maestra

HU2.1 se corresponde con RF01 (Seguridad e identidad por roles), RF03 (Gestión de
fuentes normativas y técnicas versionadas), RF11 (Preevaluación jurídica con citas
y abstención), RF12 (Recuperación trazable con metadatos y fragmentos) y RF17
(Auditoría inmutable) del documento maestro.

Asimismo, se vincula estrechamente con la Prueba de Concepto (PoC) documentada en
`6_Prueba_de_Concepto.docx`, donde se evaluó el mecanismo de recuperación RAG
agéntico (Épica 2) sobre una base normativa referencial de 24 fragmentos didácticos
de cuatro instrumentos normativos:

1. `Ley N.° 27972` (Ley Orgánica de Municipalidades)
2. `D. L. N.° 1252` (Sistema Nacional de Programación Multianual y Gestión de Inversiones - Invierte.pe)
3. `Ley N.° 32069` (Ley General de Contrataciones Públicas)
4. `PDU/PDM Huancayo-El Tambo` (Plan de Desarrollo Urbano / Metropolitano)

La documentación maestra y la PoC declaran expresamente que el contenido del PMV1
es didáctico y simulado para el ámbito de El Tambo, Huancayo; por tanto, la búsqueda
automática asiste y acelera la revisión del especialista, pero **no emite dictámenes
jurídicos vinculantes ni sustituye el criterio profesional del Asesor Jurídico**.

## Comportamiento implementado

- **Seguridad y roles (RF01):**
  - Se incorporó formalmente el rol `LEGAL_ADVISOR` ("Asesor Jurídico") en `auth_db`.
  - Se configuró la cuenta semilla de prueba `legal@siprim.test` con contraseña segura
    hasheada mediante Argon2id.
  - La dependencia `require_legal_advisor` en el backend restringe el acceso a
    los roles `LEGAL_ADVISOR` y `ADMIN`. Los usuarios con rol `PLANNER` reciben
    invariablemente `403 Forbidden`.

- **Catálogo normativo versionado (RF03 / RF12):**
  - Se creó la tabla `normative_documents` en `platform_db` para alojar los fragmentos
    normativos estructurados con: identificador único, nombre de norma, código corto,
    versión de vigencia, tema, contenido/resumen didáctico, indicador de vigencia
    (`in_force`), indicador de alerta (`has_alert`) y origen del dato (`data_origin`).
  - Se restringió a nivel SQL que el origen del dato sea únicamente `declared`,
    `simulated`, `public` u `official`.
  - Se precargaron los 24 fragmentos referenciales de la PoC, donde los fragmentos
    `PDUPDM-02` (incompatibilidad de uso de suelo) y `PDUPDM-04` (zonas de riesgo)
    poseen `has_alert = TRUE`.

- **Motor de búsqueda y ponderación de relevancia:**
  - Implementación en `NormativeSearchEngine` que extrae palabras clave útiles,
    filtra stop words en español, y pondera coincidencias en identificador (+50),
    tema (+35/+15), contenido (+25/+5) y documento (+15/+4).
  - Incluye ponderación adicional ante consultas con términos de riesgo o incompatibilidad
    cuando el fragmento es causal de alerta.
  - Ordena los resultados por puntuación de relevancia (`relevance_score`) de forma
    determinista y reproducible.

- **Detección de alertas y revisión humana obligatoria (RF11 / RNF04):**
  - Si los fragmentos recuperados contienen causales de alerta (`has_alert = TRUE`),
    el sistema retorna `requires_human_review = True` y agrega una alerta explicativa
    en `alerts_found`.
  - Cada respuesta incluye un disclaimer explícito de material referencial del PMV1.

- **Idempotencia y Auditoría (RF17):**
  - El endpoint admite la cabecera `Idempotency-Key`.
  - Se registra la consulta en `normative_search_logs` y el evento de auditoría
    `NORMATIVE_SEARCH_PERFORMED` en `audit_events`.
  - Repetir la misma consulta con la misma clave devuelve `duplicated = True`.
  - Intentar reutilizar la misma clave para una consulta diferente produce un conflicto
    `HTTP 409 Conflict`.

- **Endpoints expuestos:**
  - `POST /api/v1/normative/search`: Búsqueda automática con filtros, scoring y alertas.
  - `GET /api/v1/normative/documents`: Catálogo de normas activas y cantidad de fragmentos.

## Evidencia de validación

- **46 pruebas automatizadas aprobadas** en pytest (100% de la suite pasando).
- **10 de 10 pruebas de aceptación SQL aprobadas** sobre PostgreSQL real (`verificar.py`).
- **Verificación en vivo contra contenedores Docker:**
  - Login con `legal@siprim.test` emite token con rol `LEGAL_ADVISOR`.
  - `GET /api/v1/normative/documents` retorna los 4 grupos normativos (24 fragmentos).
  - `PLANNER` intentando buscar o listar recibe HTTP 403.
  - Búsqueda "uso de suelo incompatible con zonificacion" ubica como Top 1 a `PDUPDM-02`
    con `has_alert = True` y `requires_human_review = True`.
  - Reenvío con misma `Idempotency-Key` devuelve `duplicated = True`.
  - Reutilización con query distinta devuelve HTTP 409.
  - Registros de auditoría y log verificados directamente en `platform_db`.
