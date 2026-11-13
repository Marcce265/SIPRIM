# Auditoría inicial FURPS de SIPRIM

Fecha: 13 de noviembre de 2026. Fuente oficial: Marcce265/SIPRIM, main `1ada71a4f70a1c207bacd1105e824de3b18c1a1e`. Evaluación de código, frontend compilado y consultas HTTP no destructivas. No se atribuye ejecución real a las pruebas con dobles de servicios.

## Escala y objetivo
Cada factor recibe 5 si cumple los criterios examinados, 3 si cumple parcialmente y 1 si no cumple. Apego = PO / PD * 100. Cinco factores, PD=25. Es una rúbrica académica de esta revisión, no certificación ni cobertura total de las 26 HU. Objetivo: 5 por factor, 100%, condicionado a evidencia funcional completa.

| Factor | PO | PD | Apego | Evidencia y brecha |
|---|---:|---:|---:|---|
| Funcionalidad | 3 | 5 | 60% | Controladores PMV1, evaluaciones por dimensión, ML y métricas existentes. No se ha demostrado recorrido completo con sesión real. Carga física local según physicalExpedienteStorage.ts. |
| Usabilidad | 3 | 5 | 60% | Formularios y manejo de timeout; client.ts muestra instrucciones internas de Docker al usuario ante 500. Sin evaluación WCAG completa. |
| Confiabilidad | 3 | 5 | 60% | Errores de dominio tipificados y timeout Gemini. Falta respuesta genérica correlacionada para errores inesperados. /health solo prueba proceso vivo. |
| Rendimiento | 3 | 5 | 60% | Bundle JS 415.71 kB, gzip 119.12 kB. No hay medición p95 del flujo con BD y Gemini bajo concurrencia. |
| Mantenibilidad | 3 | 5 | 60% | Arquitectura por puertos, docs y tests. typecheck/lint/build pasan; lint registra cinco advertencias. Suite inicial sin PostgreSQL: 183 pasan, 67 fallan y 9 errores. |

Total: 15/25, 60%. Ninguna falla de conexión local se declara defecto funcional sin repetir con PostgreSQL aislado.

## Hallazgos priorizados
F01 alta: errores inesperados sin identificador para soporte. F02 media: mensaje 500 orientado al administrador, no al usuario. F03 alta: establecer evidencia reproducible y separar pruebas aisladas, integraciones y producción. F04 media: guía de uso rápido y procedimiento de recuperación. F05 media: medir rendimiento real, no confundir benchmark de cálculo sintético con carga HTTP concurrente.

Responsable técnico propuesto: Piero Martin Sierra Leiva; el equipo debe confirmar el reparto F/U/R/P/S. Meta de esta sesión: corregir F01/F02 y documentar F03/F04, dejando F05 explícito si no hay evidencia suficiente.
