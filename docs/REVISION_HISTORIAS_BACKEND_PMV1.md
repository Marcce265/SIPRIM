# Revision de las historias backend existentes del PMV1

Fecha de revision: 2026-10-01.

Fuentes de verdad usadas:

- `DOCUMENTACION_MAESTRA_SISTEMA_MULTIAGENTE.md`, version 1.0.
- `BASES_DE_DATOS_PMV1_MICROSERVICIOS.md`, version 1.0.

Los identificadores anteriores (`HU1.1`, `HU1.2`, `HU1.3`, `HU1.10`) proceden
del backlog previo. El documento maestro reorganiza el producto en HU01-HU32.
Para evitar afirmar cumplimiento con identificadores incompatibles, este informe
mantiene la trazabilidad entre ambos catálogos.

| Implementacion anterior | Equivalencia maestra | Resultado de la revision |
|---|---|---|
| HU1.1 Registro unico | HU05 y HU09, RF04/RF06 | Cumple en la ruta oficial: autentica al planificador, crea `projects` y `project_versions` una sola vez y encola la evaluacion economica mediante outbox/Celery. La clave de idempotencia evita duplicados. |
| HU1.2 Campos faltantes | HU07, RF05 | Cumple: devuelve los campos concretos y no persiste ni evalua presupuestos/beneficiarios ausentes, cero o negativos. |
| HU1.3 Evaluacion economica | HU10-HU11, RF07 | Cumple el alcance PMV1: calcula costo por beneficiario y puntaje 0-100 con criterios versionados, formula y explicacion. El retorno socioeconomico queda `null` porque no existen beneficios monetizados trazables. |
| HU1.10 Cumplimiento juridico | HU17, RF11-RF12 | Cumple solo como prevalidacion segura: sin RAG/corpus versionado se abstiene (`complies=null`), no entrega fuentes falsas y exige revision humana. El dictamen legal automatizado sigue fuera del PMV1. |
| HU1.11 Zonificacion PDU/PDM | HU17, RF11-RF12 | Implementada como prevalidacion persistente: exige ubicacion y uso propuesto, es idempotente y auditable, y bloquea en base de datos cualquier conclusion sin documento, version, localizador y fragmento. Sin corpus/GIS responde `compatible=null` y exige revision humana. |
| HU2.1 Busqueda automatica de normativa | RF01, RF03, RF11-RF12, RF17 | Implementada para el Asesor Juridico (`LEGAL_ADVISOR`): busqueda automatica con ponderacion de relevancia, stop words y deteccion de alertas sobre el corpus de 24 fragmentos normativos reales y verificables (`data_origin='public'`) de Ley 27972, DL 1252, Ley 32069 y PDM Huancayo O.M. 636-2020. Idempotente y auditada; exige revision humana ante alertas. |
| Compuerta Formal de Aprobacion Humana | HU21, RF18, HITL | Compuerta de cierre del PMV1: ningun proyecto concluye de forma puramente automatica. Tras la evaluacion tecnica (`evaluated`), solo el rol `ADMIN` puede emitir el dictamen formal (`approved`, `rejected` u `observed`). Si es `observed`, se exige el registro obligatorio de condiciones. Persistido en `human_approvals`, auditable e idempotente. |

## Bases de datos

Los esquemas `auth_db`, `platform_db` y `economic_db` coinciden con la
separacion de propiedad del modelo maestro. Docker Compose crea las tres bases,
usuarios restringidos, datos semilla y Redis. La API solo usa `auth_db` y
`platform_db`; el worker economico solo usa `economic_db`; el worker de plataforma
proyecta los eventos completados en `platform_db`. No existen joins ni claves
foraneas entre bases.

`database/schema.sql` queda como compatibilidad temporal para el adaptador
SQLAlchemy heredado; no es la base oficial del diseño PMV1. El codigo nuevo debe
usar los contratos y esquemas de las tres bases, sin JOIN ni claves foraneas
entre ellas.

## Evidencia automatizada

- Casos A y B: S/ 200 por persona = 100 puntos; S/ 300 = 66.67 puntos.
- Umbrales invertidos se rechazan.
- Expediente incompleto no genera evaluacion.
- Respuesta juridica sin fuente obliga revision humana.
- Login JWT con roles y autorizacion del planificador en servidor.
- Estados observables `queued`, `processing` y `completed`.
- Idempotencia de solicitud, consumidor economico e inbox de plataforma.
- Outbox recuperable cada 15 segundos si Redis no estaba disponible.
- El nucleo de la API puede probarse sin instalar el proveedor opcional Gemini.

## Limite funcional deliberado

HU1.10 no emite un dictamen juridico automatico: la documentacion maestra ubica
el agente juridico y RAG en un incremento posterior. Afirmar cumplimiento de la
Ley de Contrataciones sin una fuente versionada contradiria RF11/RF12. Del mismo
modo, HU1.3 no fabrica retorno social; el PMV1 solo posee presupuesto,
beneficiarios y criterios de costo.
