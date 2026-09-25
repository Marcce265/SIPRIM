-- Pruebas CRUD manuales (ejecutar en el SQL Editor de Neon/Supabase)

-- CREATE
INSERT INTO proyectos (nombre, descripcion, ubicacion, presupuesto, beneficiarios, tipo_proyecto)
VALUES ('Ciclovia Huancayo', 'Conexion segura entre distritos', 'Huancayo', 1200000, 15000, 'Movilidad urbana')
RETURNING *;

-- READ
SELECT * FROM proyectos ORDER BY id;

-- UPDATE
UPDATE proyectos SET presupuesto = 1500000
WHERE nombre = 'Ciclovia Huancayo'
RETURNING id, nombre, presupuesto;

-- DELETE
DELETE FROM proyectos WHERE nombre = 'Ciclovia Huancayo' RETURNING id;

-- Verificacion
SELECT COUNT(*) AS total FROM proyectos;
