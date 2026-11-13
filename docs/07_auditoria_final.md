# Dictamen final de calidad y seguridad SIPRIM

Evaluación de semana 13, 13 de noviembre de 2026. Fuente de desarrollo: https://github.com/Marcce265/SIPRIM. Espejo de despliegue: https://github.com/PieroMSL/SIPRIM. No se desarrolló en el espejo.

## Resultado
Calidad: cumple parcialmente, 60% inicial a 68% posterior. Seguridad: cumple parcialmente, 56% a 76% en rúbrica académica de diez categorías del material docente. Meta esperada: 100% de criterios examinados con evidencia. Estos porcentajes no certifican cobertura total de HU, ausencia de vulnerabilidades ni disponibilidad.

## Evidencia y preservación funcional
279 pruebas aprobadas con PostgreSQL 16.2 local y datos semilla aislados; una advertencia LangGraph. TypeScript, lint y build aprobados; cinco advertencias lint preexistentes. npm audit: dos hallazgos altos iniciales y cero finales. Veinte pruebas nuevas verifican autorización, claims JWT y saneamiento/correlación de errores. Test HU3.2 actualizado contra el requisito HU1.12 tras reproducir su falla en el main original.

Neon ya estaba integrado. Consulta de solo lectura del proyecto bold-moon-78123050, rama production br-purple-cloud-b6bf13k6: auth_db contiene users; platform_db tiene 48 tablas públicas, 11 proyectos y 11 versiones. No se ejecutaron semillas, migraciones ni pruebas de escritura en Neon productivo. Vercel inicial READY desplegaba exactamente main 1ada71a desde el espejo; /health respondió 200. Publicación completada mediante la sesión del usuario en Chrome. PR oficial https://github.com/Marcce265/SIPRIM/pull/12 integrado en main con commit cec94702021c26175e03a6af506f490ef367b77a. Se compararon byte por byte los 24 archivos publicados con la implementación probada. La validación JWT se aisló en ValidatedAuthService sin reemplazar el archivo grande de servicios; la suite volvió a pasar completa (279 pruebas, 7.54 s).

El espejo PieroMSL/SIPRIM recibió exactamente ese commit por avance rápido, sin desarrollo independiente. Vercel desplegó producción dpl_7mQKgtu2wYu5uSR9GWuskyY3dbSh en 35 s, estado READY. Dominio https://siprim-gemini-demo-piero-m.vercel.app/. Comprobación HTTP posterior: /health 200 con status ok; GET /api/v1/proyectos/2147483647 sin sesión devuelve 401 Autenticacion requerida, WWW-Authenticate Bearer, Cache-Control no-store, nosniff y X-Request-ID. Interfaz de acceso institucional visible. No se completó el recorrido autenticado ni llamada real a Gemini por falta de credenciales institucionales proporcionadas en esta sesión. READY no sustituye esas pruebas.

Se tomaron capturas reales de la rama oficial, los siete informes, la protección de API, el PR integrado, el registro de las 279 pruebas, Vercel Production READY y npm audit con cero hallazgos. Estas evidencias sirven para adjuntar a Trello; la captura de pruebas documenta la suite local, no una ejecución de toda la suite en producción.

## Riesgos pendientes
1. Alto: falta de cuotas/limitación distribuida observable en login y llamadas IA; diseñar control compatible con serverless.
2. Medio: token en localStorage, sin revocación inmediata demostrada; evaluar cookies HttpOnly con protección CSRF en cambio separado.
3. Medio: dependencias Python sin lock ni auditoría completa de vulnerabilidades.
4. Medio: no existe evidencia de carga HTTP concurrente real ni p95 con Neon/Gemini, ni alerta operacional externa comprobada.
5. Medio: falta recorrido visual completo con sesión institucional y llamada real a Gemini en esta sesión; pruebas de integración locales no lo sustituyen.
6. Funcional: archivos físicos siguen el mecanismo local del oficial; no se declara persistencia de documentos en servidor por tener Neon conectado.

## Recomendación
No apto para producción sin restricciones bajo los criterios estrictos de la guía. Adecuado para continuar validación académica controlada con riesgos documentados. No se atribuye aprobación total mientras existan riesgos altos. No se detectaron regresiones en la suite ejecutada; eso no garantiza ausencia de regresiones fuera de ella. Riesgo operativo residual: alto por exposición pública sin cuotas verificadas.

## Documentos de esta sesión
01_auditoria_furps.md; 02_plan_furps.md; 03_auditoria_implementacion_furps.md; 04_auditoria_owasp.md; 05_plan_owasp.md; 06_auditoria_implementacion_owasp.md; 07_auditoria_final.md. Evidencias: evidencias/semana13/.
