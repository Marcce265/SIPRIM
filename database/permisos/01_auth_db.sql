-- Ejecutar en auth_db como neondb_owner (despues de crear el rol auth_app en Neon)
REVOKE CONNECT ON DATABASE auth_db FROM PUBLIC;
GRANT  CONNECT ON DATABASE auth_db TO auth_app;
GRANT USAGE ON SCHEMA public TO auth_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO auth_app;
