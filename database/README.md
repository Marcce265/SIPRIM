# Bases de datos del PMV 1

La infraestructura local implementa las tres bases logicas definidas por el
modelo maestro. Las tres viven en una sola instancia PostgreSQL, pero cada una
tiene propietario y credenciales de aplicacion independientes:

- `auth_db` / `auth_app`
- `platform_db` / `platform_app`
- `economic_db` / `economic_app`

Redis funciona como broker y no es fuente de verdad.

## Inicio local

```powershell
docker compose up -d postgres redis
Copy-Item database/.env.example .env
```

Si Postgres ya existía con el esquema antiguo (`siprim` sin `auth_db`), inicialice PMV1 sin borrar el volumen:

```powershell
docker compose up -d postgres
python database/ensure_pm_v1.py
python database/verificar.py
```

La primera inicializacion aplica, en orden, los archivos `01_schema.sql`,
`02_seed.sql`, `03_comentarios.sql` y `04_vistas_es.sql` de cada base. Para
reaplicar de forma idempotente sobre bases ya existentes:

```powershell
python database/aplicar.py
```

Para demostrar el contrato de evaluacion economica y la idempotencia sin
depender todavia del worker Celery:

```powershell
python database/simular_flujo.py
python database/simular_flujo.py --duplicar
python database/verificar.py
```

Las contrasenas incluidas son exclusivamente de desarrollo local. No deben
usarse en un despliegue ni copiarse a servicios externos.

## Extensión HU1.11

`platform_db` conserva `location_description`, `proposed_land_use` y el origen
del dato en la versión exacta del expediente. `zoning_review_requests` registra
la prevalidación idempotente. Dos restricciones impiden guardar una conclusión
de compatibilidad sin documento, versión, localizador y fragmento, o mientras
el estado siga siendo `requires_review`.

La tabla es una solicitud/proyección de plataforma, no un agente jurídico ni un
GIS. El corpus PDU/PDM y el servicio RAG pertenecen al incremento posterior
descrito por el documento maestro.

## Extensión HU2.1 y Corpus Legal Real

`auth_db` añade el rol `LEGAL_ADVISOR` (`00000000-0000-4000-a000-000000000003`)
y el usuario de prueba `legal@siprim.test`.

`platform_db` incorpora el catálogo `normative_documents` con 24 fragmentos normativos
con texto legal real y verificable (`data_origin='public'`) extraídos de fuentes oficiales
peruanas (leyes.congreso.gob.pe, busquedas.elperuano.pe, spij.minjus.gob.pe, munihuancayo.gob.pe):
- **Ley N.° 27972** (Ley Orgánica de Municipalidades): Arts. 5, 6, 9, 20, 53, 73, 79, 80, 97.
- **D. L. N.° 1252** (Invierte.pe / TUO D.S. 242-2018-EF): Arts. 1, 3, 4, 5, 8.
- **Ley N.° 32069** (Ley General de Contrataciones Públicas): Arts. 5, 41, 46, 53, 54, 63, 64, 76, 84.
- **PDM Huancayo 2017-2037** (O.M. N.° 636-2020-MPH/CM): Zonificación, incompatibilidad, aportes RNE TH.010, riesgos SINAGERD, sistema vial y Ley DUS 31313.

Los fragmentos `PDUPDM-02` y `PDUPDM-04` activan alertas normativas (`has_alert=TRUE`),
obligando a marcar `requires_human_review=TRUE`.

Las consultas realizadas se auditan de forma idempotente en `normative_search_logs`
(con clave única `idempotency_key`), vinculándose con `audit_events` bajo el evento
`NORMATIVE_SEARCH_PERFORMED`. Se agregan las vistas `vista_fuentes_normativas` y
`vista_busquedas_normativas`.

## Compuerta Formal de Aprobación Humana (Cierre del PMV1)

Para garantizar la supervisión humana (*Human-in-the-Loop*), el resultado técnico de
los agentes y prevalidaciones no cierra automáticamente el expediente. Se incorpora la
tabla `human_approvals` en `platform_db`:

- **Restricción de flujo:** Solo proyectos con evaluación técnica finalizada (`status = 'evaluated'`)
  pueden recibir un dictamen humano formal.
- **Decisiones permitidas:** `approved`, `rejected` u `observed`.
- **Condiciones obligatorias:** Si el dictamen es `observed`, la base exige registrar
  condiciones/observaciones pendientes (`CHECK approval_observed_requires_conditions`).
- **Rol exclusivo:** Solo el rol `ADMIN` puede emitir el dictamen formal.
- **Idempotencia y trazabilidad:** Toda decisión usa `Idempotency-Key` único y registra
  evento de auditoría `PROJECT_HUMAN_APPROVAL_RECORDED`.
- **Actualización de ciclo de vida:** Al emitirse el dictamen, `projects.status` se actualiza
  a `approved`, `rejected` u `observed`.
- **Vistas en español:** `vista_aprobaciones_humanas` y actualización de `vista_proyectos`.


## PMV 2 - Sprint 2: Extensiones Territoriales y Desacoplamiento de Migraciones

### Desacoplamiento de Esquema vs. Semillas de Demostración
Las migraciones DDL (`03_migration_hu1.4.sql` y `03_migration_hu1.6.sql`) contienen exclusivamente definiciones de tablas, índices, restricciones y modificaciones de esquema (`CREATE TABLE IF NOT EXISTS`, `ALTER TABLE`, `ADD CONSTRAINT`). No insertan ni sobrescriben proyectos ni indicadores de demostración.

- Para aplicar únicamente los cambios de esquema en bases de datos existentes sin sembrar datos simulados:
  Ejecutar individualmente los archivos de migración DDL (`03_migration_hu1.4.sql`, `03_migration_hu1.6.sql`).
- Para desarrollo y pruebas locales con datos simulados (PRY-A, PRY-B, PRY-C):
  `02_seed.sql` contiene las semillas idempotentes.

### HU1.4: Accesibilidad Social Multidimensional
`platform_db` incorpora:
- `territorial_social_indicators`: Repositorio de indicadores en salud, educación y transporte.
- `social_accessibility_assessments`: Evaluaciones registradas formalmente.

### HU1.6: Evaluación de Impacto Ambiental
`platform_db` incorpora:
- `project_environmental_records`: Registros de factores ambientales territoriales.
  La columna `is_in_protected_or_risk_area` es de tres estados (`TRUE`, `FALSE`, o `NULL` / no determinado).
  La restricción `chk_env_insufficient_no_evidence` exige que si `has_sufficient_data = FALSE`, `is_in_protected_or_risk_area` sea estrictamente `NULL`, impidiendo interpretar la ausencia de datos como ausencia de riesgo.
- `environmental_assessments`: Evaluaciones con compuerta técnica y restricción que exige revisión técnica humana ante riesgo alto (`chk_high_risk_requires_human_review`).

### HU1.7: Conservación de Áreas Verdes y Regla de Demostración de Puntaje
`platform_db` incorpora:
- `project_green_area_records`: Registros de superficie, delimitación, afectación declarada vs. evidenciada y medidas de protección de áreas verdes.
- Restricción `chk_green_area_insufficient`: Exige que si `has_sufficient_data = FALSE`, los campos de superficie, delimitación, tipo de afectación y efecto en puntaje sean estrictamente `NULL`.
- Regla de demostración para el prototipo PMV2:
  - **Base ambiental (HU1.6):** Riesgo bajo (85.0 pts), riesgo moderado (70.0 pts), riesgo alto (25.0 pts).
  - **Conservación con sustento y medidas suficientes:** Bonificación de `+15.0 pts` (explicada).
  - **Afectación de áreas verdes con medidas insuficientes:** Deducción de `-20.0 pts` (explicada).
  - **Afectación mitigada con reposición equivalente:** Efecto neutro (`0.0 pts`).
  - **Información insuficiente (`CA-HU1.7-02`):** Sin ventaja ambiental automática ni bonificación (`None` / no determinado).
  - **Interacción con riesgo alto:** La bonificación nunca convierte en favorable un expediente con riesgo ambiental alto (`favorable` es estrictamente `None` / condicionado a revisión humana obligatoria).


### HU1.5: Equidad de Género y Edad
`platform_db` incorpora:
- `project_demographic_equity_records`: Registros de indicadores demográficos agregados por dimensión (`genero` y `edad`), población beneficiaria agregada, porcentaje agregado, criterios de equidad, beneficios declarados vs. evidencia verificable y medidas con enfoque de inclusión.
- Restricción `chk_equity_insufficient`: Exige que si `has_sufficient_data = FALSE`, los campos de población agregada, porcentaje agregado y efecto en el puntaje sean estrictamente `NULL` y el tipo de efecto sea `'indeterminado'`. Esto impide inferir proporciones demográficas o asignar bonificaciones automáticas sin evidencia (`CA-HU1.5-02`).
- Regla de demostración para el prototipo PMV2:
  - **Base de accesibilidad social (HU1.4):** 3 categorías completas (70.0 pts), parcial (50.0 pts), insuficiente (`None`).
  - **Dimensión Género (`genero`):**
    - Cobertura directa o medidas con perspectiva de género acreditadas: `+15.0 pts` (Favorable).
    - Sin medidas afirmativas pero sin discriminación: `0.0 pts` (Neutro).
    - Datos demográficos insuficientes: `None` / No determinado · Sin ventaja automática (`CA-HU1.5-02`).
  - **Dimensión Edad (`edad`):**
    - Cobertura a niñez (<12) o adultos mayores (≥65) con diseño universal/rampas: `+15.0 pts` (Favorable).
    - Sin impacto preferente ni barreras: `0.0 pts` (Neutro).
    - Datos etarios insuficientes: `None` / No determinado · Sin ventaja automática (`CA-HU1.5-02`).
  - **Puntaje Social Consolidado:** Suma de base y componentes verificados (acotado entre 0 y 100). Si faltan datos en un grupo, su efecto queda `None` (no determinado) y no se otorga dictamen favorable sin evidencia.
