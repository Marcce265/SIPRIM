# Revision de las cuatro historias backend existentes

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
| HU1.1 Registro unico | HU05, parte de RF04 | Se conserva el endpoint. Ahora todo proyecto expone codigo normalizado/generado y version inicial. La migracion definitiva a UUID, responsable autenticado y `project_versions` corresponde al adaptador de `platform_db`. |
| HU1.2 Campos faltantes | HU07, RF05 | Cumple la lista concreta de campos y bloquea las evaluaciones cuando el expediente esta incompleto. |
| HU1.3 Evaluacion economica | HU10-HU11, RF07 | Corregida. Calcula costo por beneficiario, puntaje 0-100 con umbrales documentados, formula, explicacion y versiones. No inventa retorno socioeconomico. |
| HU1.10 Cumplimiento juridico | HU17, RF11-RF12 | No se declara implementada. Sin RAG y fuente versionada devuelve `cumple=null`, sin fuentes y `requiere_revision=true`. El agente juridico pertenece a un incremento posterior al PMV1. |

## Bases de datos

Los esquemas `auth_db`, `platform_db` y `economic_db` coinciden con la
separacion de propiedad del modelo maestro. Se corrigio Docker Compose, que antes
levantaba solamente la tabla heredada `proyectos` en una base `siprim` y no
ejecutaba los tres esquemas nuevos. La inicializacion local ahora crea las tres
bases logicas, tres usuarios restringidos, datos semilla y Redis.

`database/schema.sql` queda como compatibilidad temporal para el adaptador
SQLAlchemy heredado; no es la base oficial del diseño PMV1. El codigo nuevo debe
usar los contratos y esquemas de las tres bases, sin JOIN ni claves foraneas
entre ellas.

## Evidencia automatizada

- Casos A y B: S/ 200 por persona = 100 puntos; S/ 300 = 66.67 puntos.
- Umbrales invertidos se rechazan.
- Expediente incompleto no genera evaluacion.
- Respuesta juridica sin fuente obliga revision humana.
- El nucleo de la API puede probarse sin instalar el proveedor opcional Gemini.

## Alcance honesto del commit

Este cambio corrige las cuatro capacidades existentes y hace reproducible la
infraestructura de datos documentada. No declara terminado el PMV1 completo:
faltan integrar autenticacion real, repositorios de `platform_db`/`economic_db`,
la tarea Celery y el recorrido API-cola-worker-DB. Esos elementos deben entrar
en los siguientes commits antes de usar la definicion de terminado del PMV1.
