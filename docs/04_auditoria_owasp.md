# Auditoría inicial OWASP Top 10 de SIPRIM

Fecha: 13 de noviembre de 2026. Misma base que auditoría FURPS. Se usa el conjunto de diez categorías facilitado por el docente (edición 2021). Revisión acotada; sin pentest destructivo ni afirmación de certificación. Evidencia verificable en rutas y archivos indicados.

| Categoría | Estado y evidencia | Impacto | Probabilidad | Severidad |
|---|---|---|---|---|
| A01 Acceso | Hallazgo S01: proyecto_controller.py y evaluacion_ia_controller.py sin Depends de autenticación; GET de ID inexistente en producción devolvió 404 sin sesión, no 401 | Consulta/modificación y consumo IA por terceros | Alta | Alta |
| A02 Criptografía | Parcial: Argon2 y JWT HS256, HTTPS en Vercel. S02: settings.py permite secreto JWT conocido de desarrollo sin bloqueo en producción | Falsificación de sesión si se despliega con valor por defecto | Media, no se conoce el valor real | Alta |
| A03 Inyección | Consultas observadas con parámetros psycopg; no se encontró exploit confirmado. No equivale a cobertura completa | Alto si apareciera concatenación insegura | No determinada | Media residual |
| A04 Diseño | Token en localStorage; sin limitador distribuido observable en login/IA. Requiere diseño de cuotas y revocación compatible con serverless | Abuso y exposición ante XSS | Media | Alta residual |
| A05 Configuración | S03: API sin no-store explícito ni nosniff; documentación OpenAPI pública. No se considera OpenAPI por sí sola vulnerabilidad | Caché de información y endurecimiento insuficiente | Media | Media |
| A06 Componentes | package-lock versionado; dependencias Python con rangos sin lock. Resultado de herramientas separado en evidencia; sin inventar CVE | Dependiente de versión vulnerable | No determinada | Media residual |
| A07 Autenticación | S04: AuthService.decode valida firma/issuer/audience pero no exige presencia de exp/sub/iat/roles | Token firmado sin expiración aceptable | Media, requiere capacidad de firma | Alta |
| A08 Integridad | ML JSON/gzip, sin pickle; integridad depende de Git y controles de escritura. Sin revisión exhaustiva de supply chain | Alteración de artefactos | Baja observada | Media residual |
| A09 Registro | S05: faltan correlación y métricas HTTP centralizadas. audit_events sí registra acciones de negocio | Diagnóstico tardío | Alta | Media |
| A10 SSRF | No se encontró fetch a URL arbitraria del usuario en controladores examinados; Gemini usa SDK y modelo configurado | Acceso a red interna si se introdujera tal función | No determinada | Baja residual |

Score académico de controles: 1=no cumple, 3=parcial/no demostrado, 5=control verificado. A01=1; A02=3; A03=3; A04=3; A05=3; A06=3; A07=3; A08=3; A09=3; A10=3. Total 28/50=56%. No es probabilidad de estar seguro. Sin acceso al secreto real no se afirma que producción use la clave por defecto.
