-- =========================================================
-- PMV 1 · auth_db · datos semilla de DESARROLLO (cuentas ficticias)
-- Contrasena de prueba de ambas cuentas: Prueba2026!  (hash Argon2id)
-- NO usar estas cuentas fuera del entorno de pruebas.
-- =========================================================
INSERT INTO roles (id, code, name) VALUES
    ('00000000-0000-4000-a000-000000000001', 'ADMIN',   'Administrador'),
    ('00000000-0000-4000-a000-000000000002', 'PLANNER', 'Planificador')
ON CONFLICT (code) DO NOTHING;

INSERT INTO users (id, email, full_name, password_hash) VALUES
    ('10000000-0000-4000-a000-000000000001', 'admin@siprim.test',   'Administrador de prueba', '$argon2id$v=19$m=65536,t=3,p=4$AkY6YFtxy7UNAZXFGK+obQ$Wd2QEQqCBe0erJ5WODBTXsq8gJLJ1fL9UjPiGEGEZz0'),
    ('10000000-0000-4000-a000-000000000002', 'planner@siprim.test', 'Planificador de prueba',  '$argon2id$v=19$m=65536,t=3,p=4$AkY6YFtxy7UNAZXFGK+obQ$Wd2QEQqCBe0erJ5WODBTXsq8gJLJ1fL9UjPiGEGEZz0')
ON CONFLICT (email) DO NOTHING;

INSERT INTO user_roles (user_id, role_id) VALUES
    ('10000000-0000-4000-a000-000000000001', '00000000-0000-4000-a000-000000000001'),
    ('10000000-0000-4000-a000-000000000002', '00000000-0000-4000-a000-000000000002')
ON CONFLICT DO NOTHING;
