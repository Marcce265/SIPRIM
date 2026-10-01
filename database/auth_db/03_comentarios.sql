-- Descripciones en espanol (los nombres siguen en ingles, segun el documento oficial)
COMMENT ON TABLE users IS 'Usuarios del sistema';
COMMENT ON COLUMN users.id IS 'Identificador unico del usuario';
COMMENT ON COLUMN users.email IS 'Correo electronico (en minusculas)';
COMMENT ON COLUMN users.full_name IS 'Nombre completo';
COMMENT ON COLUMN users.password_hash IS 'Contrasena cifrada con Argon2id (nunca en texto plano)';
COMMENT ON COLUMN users.is_active IS 'Indica si la cuenta esta activa';
COMMENT ON COLUMN users.created_at IS 'Fecha de creacion';
COMMENT ON COLUMN users.updated_at IS 'Fecha de ultima actualizacion';

COMMENT ON TABLE roles IS 'Roles del sistema (ADMIN = Administrador, PLANNER = Planificador)';
COMMENT ON COLUMN roles.id IS 'Identificador unico del rol';
COMMENT ON COLUMN roles.code IS 'Codigo del rol';
COMMENT ON COLUMN roles.name IS 'Nombre del rol';

COMMENT ON TABLE user_roles IS 'Roles asignados a cada usuario';
COMMENT ON COLUMN user_roles.user_id IS 'Usuario';
COMMENT ON COLUMN user_roles.role_id IS 'Rol asignado';
COMMENT ON COLUMN user_roles.assigned_at IS 'Fecha de asignacion';

COMMENT ON TABLE refresh_sessions IS 'Sesiones de inicio de sesion (token de renovacion cifrado)';
COMMENT ON COLUMN refresh_sessions.id IS 'Identificador de la sesion';
COMMENT ON COLUMN refresh_sessions.user_id IS 'Usuario de la sesion';
COMMENT ON COLUMN refresh_sessions.token_hash IS 'Token de renovacion cifrado';
COMMENT ON COLUMN refresh_sessions.expires_at IS 'Fecha de vencimiento';
COMMENT ON COLUMN refresh_sessions.revoked_at IS 'Fecha en que se cerro la sesion (vacio = activa)';
COMMENT ON COLUMN refresh_sessions.created_at IS 'Fecha de inicio de sesion';
