-- Cuentas institucionales de demostración (misma contraseña de capacitación: siprim2026)
-- Ejecutar si auth_db ya existía antes de ampliar 02_seed.sql
INSERT INTO users (id, email, full_name, password_hash) VALUES
    ('10000000-0000-4000-a000-000000000011', 'planificador@eltambo.gob.pe', 'Planificador Municipal', '$argon2id$v=19$m=65536,t=3,p=4$cAhSGXPECIE1eEcTFZ8FzA$gdfKnrzn/MqneeDWduMl5BDZPzS0YGQElFMfQeL9xUQ'),
    ('10000000-0000-4000-a000-000000000012', 'asesor.juridico@eltambo.gob.pe', 'Asesoría Jurídica', '$argon2id$v=19$m=65536,t=3,p=4$cAhSGXPECIE1eEcTFZ8FzA$gdfKnrzn/MqneeDWduMl5BDZPzS0YGQElFMfQeL9xUQ'),
    ('10000000-0000-4000-a000-000000000014', 'evaluador@eltambo.gob.pe', 'Evaluador técnico', '$argon2id$v=19$m=65536,t=3,p=4$cAhSGXPECIE1eEcTFZ8FzA$gdfKnrzn/MqneeDWduMl5BDZPzS0YGQElFMfQeL9xUQ'),
    ('10000000-0000-4000-a000-000000000013', 'admin@eltambo.gob.pe', 'Administración SIPRIM', '$argon2id$v=19$m=65536,t=3,p=4$cAhSGXPECIE1eEcTFZ8FzA$gdfKnrzn/MqneeDWduMl5BDZPzS0YGQElFMfQeL9xUQ')
ON CONFLICT (email) DO NOTHING;

INSERT INTO user_roles (user_id, role_id) VALUES
    ('10000000-0000-4000-a000-000000000011', '00000000-0000-4000-a000-000000000002'),
    ('10000000-0000-4000-a000-000000000012', '00000000-0000-4000-a000-000000000003'),
    ('10000000-0000-4000-a000-000000000014', '00000000-0000-4000-a000-000000000003'),
    ('10000000-0000-4000-a000-000000000013', '00000000-0000-4000-a000-000000000001')
ON CONFLICT DO NOTHING;
