-- Ejecutar en economic_db como neondb_owner (despues de crear el rol economic_app en Neon)
REVOKE CONNECT ON DATABASE economic_db FROM PUBLIC;
GRANT  CONNECT ON DATABASE economic_db TO economic_app;
GRANT USAGE ON SCHEMA public TO economic_app;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO economic_app;
