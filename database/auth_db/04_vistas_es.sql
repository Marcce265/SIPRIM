CREATE OR REPLACE VIEW vista_usuarios AS
SELECT u.full_name AS nombre, u.email AS correo, r.name AS rol,
       CASE WHEN u.is_active THEN 'Sí' ELSE 'No' END AS activo, u.created_at AS creado_en
FROM users u
JOIN user_roles ur ON ur.user_id = u.id
JOIN roles r ON r.id = ur.role_id;
