# Base de datos · PMV 1 (microservicios)

Implementa exactamente `BASES_DE_DATOS_PMV1_MICROSERVICIOS.md` v1.0: tres bases lógicas en un mismo PostgreSQL (Neon), una por servicio, sin FOREIGN KEY entre bases.

| Servicio | Base | Tablas |
|---|---|---|
| `ms-auth` | `auth_db` | users, roles, user_roles, refresh_sessions |
| `ms-platform` | `platform_db` | projects, project_versions, criteria_versions, criterion_weights, evaluations, economic_result_projections, audit_events, outbox_events, inbox_events |
| `ms-economic` | `economic_db` | economic_assessments, assessment_metrics, processed_requests |

## Archivos

```
database/
├── auth_db/       01_schema.sql · 02_seed.sql (cuentas ADMIN y PLANNER) · 03_comentarios.sql
├── platform_db/   01_schema.sql · 02_seed.sql (proyectos A y B, política v1) · 03_comentarios.sql
├── economic_db/   01_schema.sql · 03_comentarios.sql
├── consultas_en_espanol.sql   consultas para ver los datos con columnas en español
│   (cada base incluye además 04_vistas_es.sql: vistas en español)
├── permisos/      un usuario por servicio con acceso solo a su base (sección 10)
├── aplicar.py         crea tablas y datos semilla en las 3 bases
├── simular_flujo.py   simula el flujo de la sección 6 sin backend
├── verificar.py       pruebas de aceptación de la sección 11
└── .env.example
```

## Idioma

Los nombres de tablas y columnas están en inglés, tal como los define el documento oficial (el backend los usa así). Cada tabla y columna tiene una **descripción en español** (`03_comentarios.sql`), y `consultas_en_espanol.sql` muestra los datos con encabezados en español. Además, cada base tiene **vistas en español** (`vista_usuarios`, `vista_proyectos`, `vista_evaluaciones`, `vista_criterios`, `vista_auditoria`, `vista_resultados_economicos`, `vista_indicadores`) que solo leen las tablas originales; el backend sigue usando las tablas en inglés.

## Pasos

1. Neon → *Databases → Add database*: `auth_db`, `platform_db`, `economic_db`.
2. Copiar `.env.example` como `.env` **fuera** de la carpeta `database` y pegar la URL de cada base (*Connect*), con prefijo `postgresql+psycopg://` y sin `&channel_binding=require`.
3. Terminal:
   ```
   pip install "psycopg[binary]" python-dotenv
   python database/aplicar.py
   python database/simular_flujo.py
   python database/simular_flujo.py --duplicar
   python database/verificar.py
   ```
4. Permisos por servicio: ver `permisos/README_permisos.md`.

## Datos semilla (ficticios)

| Dato | Valor |
|---|---|
| Cuentas | `admin@siprim.test` (ADMIN) · `planner@siprim.test` (PLANNER) · contraseña de prueba `Prueba2026!` (hash Argon2id) |
| Política v1 | ECONOMIC = 100 % · excelente S/ 200 · inaceptable S/ 500 |
| Proyecto A | S/ 120 000 · 600 beneficiarios → S/ 200 por persona → 100 puntos |
| Proyecto B | S/ 90 000 · 300 beneficiarios → S/ 300 por persona → 66,67 puntos |

## Pruebas cubiertas por la base de datos

| Prueba (sección 11) | Cómo se comprueba |
|---|---|
| 2, 3, 4, 5, 6, 7, 8 | `verificar.py` (PASA / FALLA) |
| 6 · idempotencia | `simular_flujo.py --duplicar`: no se crean evaluaciones, assessments ni proyecciones nuevas |
| 9 · persistencia | los datos siguen en Neon tras cerrar VS Code y volver a ejecutar `verificar.py` |
| 10 · aislamiento | con `permisos/`, `economic_app` recibe *permission denied for database "platform_db"* |
| 1 · login y 403 | requiere el backend de `ms-auth`; la base ya tiene cuentas, roles y hash |

`simular_flujo.py` reproduce la lógica descrita para probar la base; **no reemplaza** a los microservicios reales.
