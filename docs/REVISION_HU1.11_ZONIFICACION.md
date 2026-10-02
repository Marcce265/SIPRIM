# Revisión e implementación de HU1.11

Fecha de revisión: 2026-10-01.

## Historia heredada

Como Planificador, quiero verificar que el proyecto respete la zonificación
PDU/PDM para evitar conflictos de uso de suelo.

## Correspondencia con la documentación maestra

HU1.11 se corresponde con RF11, RF12 y HU17 del documento maestro. Una alerta
territorial debe mostrar documento, versión y fragmento, y debe abstenerse y
exigir revisión cuando no haya evidencia. El mismo documento ubica el corpus
RAG jurídico, HITL y GIS después del PMV1 económico y reconoce que faltan datos
territoriales reales.

La prueba de concepto usa resúmenes didácticos simulados de PDU/PDM. Declara
expresamente que no son artículos oficiales y que no deben utilizarse para un
dictamen legal. Por ello esos fragmentos no se cargan como evidencia productiva.

## Comportamiento implementado

- El expediente oficial guarda ubicación, uso propuesto y origen del dato en
  `project_versions`.
- `POST /api/v1/projects/{id}/zoning-precheck` requiere autenticación PLANNER e
  `Idempotency-Key`.
- La solicitud se persiste en `zoning_review_requests` y genera un evento de
  auditoría `ZONING_REVIEW_REQUESTED`.
- Sin corpus PDU/PDM oficial/versionado ni geometría GIS se devuelve
  `status=requires_review`, `compatible=null`, `evidence=[]` y una limitación
  explícita.
- PostgreSQL rechaza una conclusión `compatible=true/false` si falta documento,
  versión, localizador o fragmento, y también rechaza conclusiones durante el
  estado `requires_review`.

## Alcance pendiente

La compatibilidad territorial automática no se declara terminada. Para emitir
una alerta sustentada se debe implementar el incremento RAG jurídico con fuentes
oficiales vigentes, sus modificaciones, localizadores verificables y revisión
humana. Para comprobar un predio específico también se necesita su geometría y
una capa de zonificación GIS aplicable.

## Evidencia de validación

- 33 pruebas automatizadas del backend aprobadas.
- 9 pruebas de aceptación SQL aprobadas sobre PostgreSQL real.
- Esquemas reaplicados sin duplicar datos ni objetos.
- Recorrido Docker verificado: login, proyecto, Celery/Redis, agente económico,
  proyección completada y prevalidación territorial.
- Repetir la clave para el mismo expediente devuelve el mismo resultado; usarla
  en otro expediente devuelve conflicto HTTP 409.
- El caso sin ubicación ni uso propuesto devuelve ambos campos faltantes y no se
  persiste.
