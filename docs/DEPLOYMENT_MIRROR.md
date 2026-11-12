# SIPRIM: fuente oficial y espejo de despliegue

## Propiedad del código

- Desarrollo y pull requests: https://github.com/Marcce265/SIPRIM
- Única rama de origen: `Marcce265/SIPRIM/main`.
- Espejo exclusivo de despliegue: https://github.com/PieroMSL/SIPRIM, rama `main`.
- Proyecto existente: https://vercel.com/piero-m/siprim-gemini-demo
- Dominio conservado: https://siprim-gemini-demo-piero-m.vercel.app/

Nunca desarrollar funcionalidades en el espejo. Los cambios funcionales y de infraestructura de este documento se proponen primero mediante PR en el oficial. La rama `preview/official-vercel-validation` del espejo copia commits de la rama oficial de preparación; no contiene desarrollo independiente.

## Sincronización

`.github/workflows/sync-deployment-mirror.yml` compara ambos `main` cada hora (minuto 17 UTC; GitHub puede retrasar ejecuciones). Solo ejecuta el trabajo en `PieroMSL/SIPRIM`; en el original se omite. También dispone de **Run workflow** para sincronización inmediata. **Sync fork → Update branch** es otra opción manual cuando no hay divergencia.

Usa el `GITHUB_TOKEN` efímero del propio workflow, limitado a escritura de contenido del espejo. No requiere token personal ni acceso de escritura al repositorio oficial. No usa servicios de pago ni una computadora permanente. No se ejecuta por push, por lo que no genera bucles.

Solo permite avance rápido y registra SHA de origen, destino anterior y destino posterior en el resumen de ejecución. Una divergencia o actualización concurrente incompatible falla sin `force`. Los errores quedan en Actions y siguen las preferencias de notificación del propietario. Nunca resolverlos mezclando automáticamente cambios del espejo hacia el oficial.

Los forks pueden requerir habilitar Actions y los workflows programados. Si GitHub bloquea su ejecución por facturación o permisos, no considerar operativa la sincronización hasta comprobar un mecanismo alternativo. Los programados pueden suspenderse tras 60 días sin actividad en repositorios públicos; revisar Actions periódicamente.

## Vercel

Git conectado permanentemente al espejo; rama de producción `main`. `vercel.json` compila Vite y publica `api/index.py` como entrada ASGI de `backend.main:app`. `/api/*`, `/health`, OpenAPI y documentación pasan al backend; recursos estáticos y rutas React pasan al frontend.

La API del frontend usa el mismo origen en producción y conserva el destino local solo para desarrollo. `pyproject.toml` declara dependencias Python porque Vercel lo prioriza sobre `requirements.txt`. Mantener ambos archivos coherentes.

En Vercel, `ServerlessTaskDispatcher` ejecuta dentro de la petición los mismos procesadores económicos idempotentes y su proyección persistente. Fuera de Vercel permanece Celery. No inicia workers ni usa archivos locales como persistencia. Si falla el procesamiento, el evento outbox sigue pendiente; su recuperación necesita reejecución explícita y monitoreo, no un daemon ficticio.

Conservar las variables privadas existentes `DATABASE_URL`, `AUTH_DB_URL`, `PLATFORM_DB_URL`, `ECONOMIC_DB_URL`, `JWT_SECRET`, `GEMINI_API_KEY`, `AI_MODEL` y `USE_IN_MEMORY_REPOSITORY=false`. No poner sus valores en Git, logs ni documentación. Las variables históricas de demostración no habilitan mecanismos nuevos de autenticación en esta rama.

## Datos y migraciones

Neon requiere el esquema del main oficial: `database/platform_db/01_schema.sql` y sus migraciones numeradas. Revisar y aplicar de forma transaccional; no ejecutar semillas en producción. Antes de actualizar el esquema se creó el respaldo `backup-before-official-schema-20261112` (`br-summer-dream-b6n3h3d9`), sin compute dedicado. No reemplazar documentos ni expedientes existentes. Las pruebas automatizadas usan PostgreSQL local aislado.

## Diferencias históricas que no se incorporan

El despliegue anterior `6aa9226e84f3024751a93d137bb59fff527d193a` incluía persistencia y descarga fragmentada de documentos en Neon, exclusiva de la antigua copia de Piero. El main oficial conserva la carga física en el navegador y no expone esa misma API de documentos. Sus tablas existentes se conservan; este trabajo no importa silenciosamente aquella implementación ni declara equivalencia funcional. También hay tablas históricas de checkpoints y evaluaciones con otros nombres que no sustituyen el esquema oficial.

## Validación y promoción

Ejecutar TypeScript, lint, build y pytest con PostgreSQL. Validar después el preview: frontend, API, sesión institucional, permisos, consulta de expediente, Gemini, esquema de Neon y logs. Un estado READY por sí solo no demuestra que funcione la API. La promoción al dominio debe esperar a las pruebas críticas. Conservar la versión anterior disponible para reversión. Los resultados concretos de la intervención se registran en el PR y en el informe de entrega.
