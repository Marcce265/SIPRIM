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
