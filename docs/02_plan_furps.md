# Plan de mejora FURPS de SIPRIM

Base: 01_auditoria_furps.md. Cambios incrementales en el oficial; espejo solo recibe commits del oficial. Sin migraciones ni alteración de datos de producción.

| ID | Objetivo y justificación | Prioridad | Riesgo y dependencias | Validación | Reversión |
|---|---|---|---|---|---|
| F01 | Errores 500 genéricos, request ID y registro sin payloads ni tokens para diagnóstico | Alta | Bajo; middleware FastAPI | Excepción deliberada en TestClient, cuerpo sin secretos y correlación | Revertir commit de middleware |
| F02 | Mensaje 500 comprensible para el usuario | Media | Bajo; cliente compartido TS | typecheck, lint, build; inspección del texto | Revertir client.ts |
| F03 | Registrar baseline y resultado posterior con entornos explícitos | Alta | Medio; PostgreSQL local y dependencias | Suite completa y clasificación de limitaciones | No cambia comportamiento |
| F04 | Guía breve de operación, soporte y rollback | Media | Bajo; documentación | Revisar contra rutas y roles reales | Revertir documentación |
| F05 | Latencia p50/p95 y tasa de errores con BD y Gemini reales | Media | Requiere sesión institucional y entorno de carga autorizado | Prueba HTTP concurrente con datos aislados; objetivo académico promedio <7 s, IA separada | Detener carga; no usar producción para carga masiva |

Orden: baseline, F01/F02, pruebas, F03/F04, revisión independiente de evidencias, seguridad, dictamen global. No declarar F05 cumplido por velocidad de inferencia local. Meta aspiracional 25/25; puntaje final depende de evidencia.
