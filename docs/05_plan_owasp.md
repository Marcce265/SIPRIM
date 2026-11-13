# Plan de remediación OWASP de SIPRIM

| ID | Riesgo y objetivo | Prioridad | Componentes y mitigación | Validación | Rollback |
|---|---|---|---|---|---|
| S01 | Acceso anónimo a API antigua | Alta | Dependencias existentes: lectura planner/legal; escritura y Gemini planner. Cliente legacy envía sesión existente | Sin token 401; rol ajeno 403; planner conserva registro/consulta/evaluación; legal solo lectura | Revertir commit; no desactivar autorización para ocultar fallos |
| S02 | Clave JWT por defecto en producción | Alta | Validación Settings para APP_ENV production/preview o VERCEL=1, exige secreto propio de al menos 32 bytes | Configuración insegura rechazada, desarrollo local preservado | Revertir guardia si impide arranque y configurar secreto antes de reintentar |
| S03 | Respuestas API cacheables y falta de cabeceras | Media | no-store en API, nosniff y política de referente, sin CSP restrictiva que rompa UI | TestClient y comprobación HTTP en despliegue | Revertir middleware |
| S04 | Claims JWT incompletos | Alta | Exigir exp, iat, sub, roles, iss, aud y tipos coherentes de identidad/roles | Tokens firmados incompletos o malformados rechazados; token normal aceptado | Revertir cambio decode |
| S05 | Falta de correlación HTTP | Media | Reutilizar F01, sin datos personales ni secretos en logs | Error simulado con sentinel privado; ID en cuerpo/cabecera/log | Revertir middleware |

S06 pendiente de diseño: limitación distribuida de intentos y cuotas IA. No usar contadores en memoria como solución serverless. S07: lock Python y auditoría de dependencias. S08: migración de almacenamiento de token requiere diseño CSRF/sesiones y pruebas del frontend, fuera de parche incremental seguro. Estos riesgos impiden dictamen incondicional de producción.

Orden S01, S04, S02, S03/S05; ejecutar pruebas de roles y regresiones antes de sincronizar. Sin cambios de BD ni creación de usuarios. Probar con identidades locales de prueba, no credenciales productivas inventadas.
