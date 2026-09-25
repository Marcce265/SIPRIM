# Base de datos SIPRIM (PostgreSQL)

Scripts SQL del equipo y conexión con el backend FastAPI.

## Archivos

| Archivo | Uso |
|---------|-----|
| `schema.sql` | Crea tablas `proyectos`, `evaluaciones_economicas`, `evaluaciones_juridicas` |
| `crud_pruebas.sql` | Inserts/consultas manuales de prueba |

## Opción A — Docker (recomendado en local)

Desde la raíz del repo:

```powershell
docker compose up -d db
```

La primera vez aplica `schema.sql` automáticamente. Credenciales por defecto:

- Host: `localhost:5432`
- Base: `siprim`
- Usuario / clave: `postgres` / `postgres`

En `.env` del backend:

```dotenv
USE_IN_MEMORY_REPOSITORY=false
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/siprim
```

Verificar conexión:

```powershell
python scripts/check_database.py
```

## Opción B — Neon / Supabase (nube)

1. Crear proyecto PostgreSQL en [Neon](https://neon.tech) o [Supabase](https://supabase.com).
2. Abrir el **SQL Editor** y pegar el contenido de `schema.sql`.
3. Copiar la URL de conexión (formato `postgresql://...`).
4. En `.env`, convertir a driver psycopg v3:

```dotenv
USE_IN_MEMORY_REPOSITORY=false
DATABASE_URL=postgresql+psycopg://usuario:clave@host.neon.tech/siprim?sslmode=require
```

## Opción C — PostgreSQL instalado en Windows

```powershell
createdb siprim
psql -d siprim -f database/schema.sql
```

## Reiniciar esquema (solo desarrollo)

```powershell
docker compose down -v
docker compose up -d db
```

Esto borra los datos del contenedor y vuelve a ejecutar `schema.sql`.

## Notas

- El frontend **no** se conecta a la BD; solo consume la API REST.
- Si `USE_IN_MEMORY_REPOSITORY=true`, el backend ignora PostgreSQL.
- El esquema puede evolucionar; cuando el equipo actualice `schema.sql`, reaplicar en entornos de desarrollo.
