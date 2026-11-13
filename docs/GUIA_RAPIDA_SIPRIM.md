# Guía rápida de operación y soporte SIPRIM

## Uso institucional
1. Ingresar por https://siprim-gemini-demo-piero-m.vercel.app/ e iniciar sesión con la cuenta institucional asignada. No compartir contraseña ni token.
2. El planificador registra el expediente, completa datos y consulta su versión vigente. Valida el expediente antes de solicitar evaluaciones. Revisa resultados por dimensión y la validación de IA preliminar.
3. Asesoría jurídica atiende hallazgos y alertas normativas. Gerencia revisa el resultado integral y las aprobaciones según su rol. Una sola dimensión económica favorable no permite aprobar un expediente incompleto. Los puntos de control se resuelven para su versión correspondiente.

Estas son tres etapas de orientación, no una afirmación de que cualquier operación se complete en tres clics. La carga física local del oficial no equivale a almacenar documentos en Neon.

## Incidencias
Si expira la sesión, ingresar otra vez. Ante 403 solicitar al administrador revisar el rol, sin intentar saltar permisos. Ante 409 revisar la versión, los datos faltantes, alertas y dimensiones pendientes. Ante timeout intentar luego; el dictamen IA puede demorar más que una consulta normal. Si hay 500 anotar hora, operación e identificador X-Request-ID de la respuesta para soporte; nunca enviar contraseñas.

## Validación técnica
Instalar requirements.txt y ejecutar python -m pytest con PostgreSQL aislado y bootstrap database/bootstrap.sh del repositorio (ver database/README.md). Nunca aplicar semillas o pruebas que escriben a las URLs de producción. En frontend: npm ci, npm run typecheck, npm run lint, npm run build y npm audit. Las pruebas Gemini usan dobles; validar Gemini real por separado con expediente controlado.

## Despliegue y reversión
Desarrollar y revisar en Marcce265/SIPRIM. Sincronizar solo por avance rápido al espejo PieroMSL/SIPRIM; nunca editar ahí. Vercel conserva rama main. Comprobar /health, página de inicio, 401 anónimo, roles, consulta con sesión y logs antes de declarar éxito. Para rollback seleccionar el despliegue productivo previo en Vercel; revertir el commit en el oficial y sincronizarlo. No hay migraciones en este parche. JWT_SECRET propio, al menos 32 bytes, obligatorio en Vercel; configurar en el panel sin copiar su valor a Git o informes.
