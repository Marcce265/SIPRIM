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

## Extensión HU2.1

`auth_db` añade el rol `LEGAL_ADVISOR` (`00000000-0000-4000-a000-000000000003`)
y el usuario de prueba `legal@siprim.test`.

`platform_db` incorpora el catálogo `normative_documents` con los 24 fragmentos
versionados de la Prueba de Concepto correspondientes a cuatro normas base (Ley 27972,
D.L. 1252, Ley 32069 y PDU/PDM Huancayo-El Tambo). Solo los fragmentos `PDUPDM-02`
y `PDUPDM-04` activan alertas normativas (`has_alert=TRUE`), obligando a marcar
`requires_human_review=TRUE`.

Las consultas realizadas se auditan de forma idempotente en `normative_search_logs`
(con clave única `idempotency_key`), vinculándose con `audit_events` bajo el evento
`NORMATIVE_SEARCH_PERFORMED`. Se agregan además las vistas en español
`vista_fuentes_normativas` y `vista_busquedas_normativas`.
