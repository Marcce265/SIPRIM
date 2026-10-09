-- Rol SUPERADMIN: acceso total PMV1 (pruebas / soporte). Solo desarrollo.
INSERT INTO roles (id, code, name) VALUES
    ('00000000-0000-4000-a000-000000000004', 'SUPERADMIN', 'Superadministrador')
ON CONFLICT (code) DO NOTHING;

-- Prueba2026! (mismo hash que admin@siprim.test)
INSERT INTO users (id, email, full_name, password_hash) VALUES
    ('10000000-0000-4000-a000-000000000021', 'superadmin@siprim.test', 'Superadmin de prueba', '$argon2id$v=19$m=65536,t=3,p=4$AkY6YFtxy7UNAZXFGK+obQ$Wd2QEQqCBe0erJ5WODBTXsq8gJLJ1fL9UjPiGEGEZz0'),
    ('10000000-0000-4000-a000-000000000022', 'superadmin@eltambo.gob.pe', 'Superadmin SIPRIM', '$argon2id$v=19$m=65536,t=3,p=4$cAhSGXPECIE1eEcTFZ8FzA$gdfKnrzn/MqneeDWduMl5BDZPzS0YGQElFMfQeL9xUQ')
ON CONFLICT (email) DO NOTHING;

INSERT INTO user_roles (user_id, role_id) VALUES
    ('10000000-0000-4000-a000-000000000021', '00000000-0000-4000-a000-000000000004'),
    ('10000000-0000-4000-a000-000000000022', '00000000-0000-4000-a000-000000000004')
ON CONFLICT DO NOTHING;
