# Informe de Implementación: Compuerta de Aprobación Humana y Corpus Normativo Real

**Proyecto:** SIPRIM — PMV1 (Prototipo para Despliegue)  
**Fecha:** 2026-10-01  
**Rama:** `backend`  
**Estado:** Completo y verificado

---

## 1. Contexto y Objetivos

Para considerar el **PMV1 completamente listo para prototipo y despliegue**, se completaron dos requerimientos arquitectónicos críticos:

1. **Sustitución de resúmenes didácticos por texto legal real y verificable:**
   - Se reemplazaron los 24 fragmentos normativos didácticos/simulados de `normative_documents` por artículos y citas literales extraídas de fuentes oficiales peruanas.
   - El atributo `data_origin` pasó de `'simulated'` a `'public'`.
   - Se incluyeron identificadores oficiales de normas, artículos exactos, enlaces y metadatos de aprobación.

2. **Compuerta formal de aprobación humana (*Human-in-the-Loop* - HITL):**
   - El sistema multiagente (agente económico, prevalidación territorial y búsqueda normativa) asiste la toma de decisiones, pero **no declara unilateralmente un proyecto como definitivo**.
   - Se implementó una compuerta formal obligatoria: antes de que un expediente se considere dictaminado, un funcionario con rol `ADMIN` debe emitir una resolución humana (`approved`, `rejected` u `observed`).
   - Se implementaron restricciones estrictas en base de datos para exigir condiciones en caso de observaciones y preservar la trazabilidad auditada de toda decisión.

---

## 2. Corpus Normativo Real

Se incorporaron 24 fragmentos normativos reales agrupados en cuatro cuerpos legales vigentes aplicables al ámbito municipal de Huancayo y El Tambo:

| Grupo | Norma Oficial | Fuente Oficial | Artículos y Temas Cubiertos |
|---|---|---|---|
| `LEY_27972` | Ley N.° 27972 — Ley Orgánica de Municipalidades | `leyes.congreso.gob.pe` | Arts. 73 (Competencias municipales), 79 (Uso del suelo), 5 y 9 (Concejo municipal), 6 y 20 (Alcaldía), IV TP, 73.2 y 80 (Servicios públicos), IX TP, 53 y 97 (Presupuesto participativo). |
| `DL_1252` | D.L. N.° 1252 — Invierte.pe (TUO D.S. N.° 242-2018-EF) | `busquedas.elperuano.pe` / `mef.gob.pe` | Arts. 4.1.a (Programación multianual), 4.1.b (Formulación y evaluación), 4.1.c y 4.3 (Ejecución), 1 y 3.a (Cierre de brechas), 4.1.d, 5.2 y 8 (Seguimiento), 5 (Órganos OPMI, UF, UEI). |
| `LEY_32069` | Ley N.° 32069 — Ley General de Contrataciones Públicas | `busquedas.elperuano.pe` (24/06/2024) / `spij.minjus.gob.pe` | Arts. 5 (Principios: valor por dinero, integridad, transparencia), 46 (Requerimiento y PMBSO), 53-54 (Métodos de selección), 63-64 (Modificaciones y adicionales), 76 y 84 (Controversias y arbitraje), 41 (PLADICOP). |
| `PDU_EL_TAMBO` | Plan de Desarrollo Metropolitano Huancayo 2017-2037 (O.M. N.° 636-2020-MPH/CM) | `munihuancayo.gob.pe` / SIGRID CENEPRED | Título III (Zonificación urbana: RDM, RDA, CZ, E, H, ZRP), Índice de Usos (Incompatibilidad y uso no conforme - ALERTA), RNE TH.010 (Aportes reglamentarios), SINAGERD/SIGRID (Zonas de riesgo no mitigable: Shullcas, Mantaro - ALERTA), Reglamento Sistema Vial Metropolitano (Vías expresas, arteriales y colectoras), Ley DUS 31313 (Espacios públicos intangibles). |

---

## 3. Arquitectura de la Compuerta de Aprobación Humana

### 3.1 Esquema de Base de Datos (`platform_db`)

```sql
CREATE TABLE IF NOT EXISTS human_approvals (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    project_version_id UUID NOT NULL REFERENCES project_versions(id) ON DELETE RESTRICT,
    decision VARCHAR(24) NOT NULL
        CHECK (decision IN ('approved', 'rejected', 'observed')),
    justification TEXT NOT NULL CHECK (length(btrim(justification)) > 0),
    conditions TEXT,
    decided_by_user_id UUID NOT NULL,
    idempotency_key VARCHAR(120) NOT NULL UNIQUE,
    decided_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT approval_observed_requires_conditions CHECK (
        decision <> 'observed' OR (
            NULLIF(btrim(conditions), '') IS NOT NULL
        )
    )
);
```

- La restricción `approval_observed_requires_conditions` impide en el motor PostgreSQL que un expediente quede en estado "observado" sin indicar las observaciones o condiciones que debe subsanar el planificador.
- El estado del proyecto (`projects.status`) se extiende a: `'draft'`, `'ready'`, `'evaluating'`, `'evaluated'`, `'approved'`, `'rejected'`, `'observed'`, `'error'`.
- La vista `vista_aprobaciones_humanas` expone en español el dictamen, justificante y actor.

### 3.2 Servicio y Reglas de Negocio

- **Precondición técnica:** Solo proyectos con evaluación técnica finalizada (`status = 'evaluated'`) pueden recibir aprobación humana. Si el proyecto está en borrador o en evaluación, se rechaza la solicitud.
- **Autorización estricta:** Solo el rol `ADMIN` puede invocar `submit_human_approval`. Los roles `PLANNER` y `LEGAL_ADVISOR` reciben HTTP 403 Forbidden.
- **Idempotencia:** La clave `Idempotency-Key` evita resoluciones duplicadas. Una petición repetida devuelve el dictamen existente con `duplicated = true`.
- **Auditoría inmutable:** Cada dictamen inserta un registro en `audit_events` bajo la acción `PROJECT_HUMAN_APPROVAL_RECORDED`.

### 3.3 Endpoints API

1. `POST /api/v1/projects/{project_id}/approval`
   - **Rol:** `ADMIN`
   - **Cabecera obligatoria:** `Idempotency-Key`
   - **Cuerpo:** `{"decision": "approved"|"rejected"|"observed", "justification": "...", "conditions": "..."}`
   - **Respuesta:** 200 OK con `HumanApprovalResponse`

2. `GET /api/v1/projects/{project_id}/approval`
   - **Rol:** `PLANNER` o `ADMIN`
   - **Respuesta:** 200 OK con `HumanApprovalStatusResponse` indicando estado de compuerta (`is_evaluated`, `requires_human_approval`, `current_approval`).

---

## 4. Matriz de Pruebas y Validación

### 4.1 Pruebas Unitarias de Backend (`pytest`)
- **Total ejecutadas:** 55 pruebas automatizadas (todas pasaron en 4.13s).
- Cobertura completa de:
  - Carga única de expediente y cálculo de campos faltantes (HU1.1, HU1.2).
  - Cálculo de costo por beneficiario y fórmula explicable (HU1.3).
  - Abstención legal segura sin fuentes (HU1.10).
  - Prevalidación territorial de zonificación con restricciones (HU1.11).
  - Búsqueda normativa con scoring, stop words, alertas e idempotencia (HU2.1).
  - Seguridad y roles: 401 sin token, 403 a roles no autorizados.
  - Compuerta de aprobación humana: validación de justificación, obligatoriedad de condiciones en observación, rechazo por falta de rol, idempotencia y conflictos de clave.

### 4.2 Pruebas de Base de Datos (`database/verificar.py`)
- **11 de 11 pruebas pasaron:**
  1. Hashes Argon2id y roles en `auth_db`.
  2. Proyectos A y B con versiones en `platform_db`.
  3. Criterios y pesos al 100%.
  4. Resultados de costo y puntaje.
  5. Proyecciones sincronizadas con `economic_db`.
  6. Ausencia de duplicados entre bases.
  7. Inmutabilidad de versiones anteriores.
  8. Restricciones SQL de presupuestos y umbrales.
  9. Restricciones SQL territoriales de HU1.11.
  10. Catálogo normativo con 24 fragmentos reales (`public`) y rol `LEGAL_ADVISOR`.
  11. Restricciones e integridad de `human_approvals` y vistas en español.

### 4.3 Validación Integral E2E en Contenedores Docker
- Verificado en vivo en los 5 contenedores (`siprim-postgres`, `siprim-redis`, `siprim-api`, `siprim-platform-worker`, `siprim-economic-worker`):
  - Creación de proyecto real.
  - Encolado y procesamiento asíncrono con Celery worker (< 1s).
  - Consulta de compuerta con estado `requires_human_approval = True`.
  - Intento de aprobación por planificador rechazado con HTTP 403.
  - Aprobación formal por administrador aceptada con HTTP 200.
  - Verificación final de proyecto en estado `approved` y compuerta cerrada.
