# Verificación de remediación OWASP

13 de noviembre de 2026. Revisión de código y pruebas automatizadas, no pentest externo independiente.

| ID | Estado | Evidencia verificable | Riesgo residual |
|---|---|---|---|
| S01 | Corregida en código | Rutas legacy dependen de roles existentes; seis rutas sin sesión devuelven 401; CITIZEN y LEGAL_ADVISOR no pueden escribir/llamar IA; cliente legacy envía bearer | Requiere comprobación del despliegue; control por rol no equivale a aislamiento entre municipios |
| S02 | Corregida en código | Settings rechaza secreto por defecto/corto en production, preview y VERCEL=1; desarrollo conserva compatibilidad | No certifica entropía de un secreto personalizado; no se inspeccionó ni publicó su valor |
| S03 | Corregida en API | Middleware establece Cache-Control no-store en /api, X-Content-Type-Options y política de referente | La cabecera debe comprobarse en Vercel; no se impone CSP sin verificar frontend |
| S04 | Corregida | ValidatedAuthService, inyectado por dependencies.py, requiere exp/iat/sub/roles/iss/aud, UUID de identidad y lista de roles string | Revocación y verificación en BD de usuario desactivado durante sesión siguen pendientes |
| S05 | Parcial | request ID en respuestas y logs sanitizados; prueba sentinel impide fuga de excepción | No hay alertas ni colector externo verificado |
| S07 componentes frontend | Corregida en alcance npm | npm audit detectó dos dependencias altas, source-map-js y Vite; npm audit fix actualizó lock compatible; auditoría final cero | Dependencias Python sin lock ni escaneo exhaustivo; cero npm no implica cero vulnerabilidades del sistema |

Veinte pruebas nuevas de seguridad aprobadas; suite total 279. Pruebas de negocio legacy usan identidad PLANNER explícita de prueba; pruebas sin autenticación separadas no omiten controles. No se sustituyeron credenciales productivas ni se desactivó IA.

Score posterior académico: A01=5, A02=5, A03=3, A04=3, A05=5, A06=3, A07=5, A08=3, A09=3, A10=3: 38/50=76%, frente a 56%. A04 permanece parcial con riesgo alto por falta de cuotas distribuidas y almacenamiento bearer en localStorage. Faltan revisión por objeto/organización, alertas y auditoría Python. No apto para producción sin restricciones según criterios estrictos de la guía mientras persistan riesgos altos no mitigados.
