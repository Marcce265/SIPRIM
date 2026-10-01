# Permisos por servicio (sección 10 del modelo)

1. En Neon → **Roles → Add role**, crear: `auth_app`, `platform_app`, `economic_app` (Neon genera la contraseña; guardarla en el `.env` de cada servicio, nunca en GitHub).
2. Ejecutar cada script **en su base**, con el usuario dueño (`neondb_owner`), desde el SQL Editor:
   - `01_auth_db.sql` en `auth_db`
   - `02_platform_db.sql` en `platform_db`
   - `03_economic_db.sql` en `economic_db`
3. Resultado: cada usuario de aplicación solo puede conectarse y escribir en **su** base. `platform_app` solo puede **insertar** en `audit_events`.
