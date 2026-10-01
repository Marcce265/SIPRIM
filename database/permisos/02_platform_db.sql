-- Ejecutar en platform_db como neondb_owner (despues de crear el rol platform_app en Neon)
REVOKE CONNECT ON DATABASE platform_db FROM PUBLIC;
GRANT  CONNECT ON DATABASE platform_db TO platform_app;
GRANT USAGE ON SCHEMA public TO platform_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO platform_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO platform_app;
-- audit_events: solo insercion y lectura para la aplicacion (no UPDATE ni DELETE)
REVOKE UPDATE, DELETE ON audit_events FROM platform_app;
