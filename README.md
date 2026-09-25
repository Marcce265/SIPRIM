# SIPRIM Backend - HU1.1

Backend funcional para registrar una sola vez el expediente basico de un proyecto
urbano y dejarlo disponible para futuros agentes especialistas.

## Arquitectura

Se usa arquitectura hexagonal (puertos y adaptadores):

- `domain`: entidad `Proyecto`, estado, reglas y puerto del repositorio. No depende
  de FastAPI, Pydantic ni SQLAlchemy.
- `application`: DTOs y casos de uso para registrar y consultar proyectos.
- `infrastructure/input`: controladores REST de FastAPI.
- `infrastructure/output`: repositorio en memoria y adaptador SQLAlchemy.
- `infrastructure/config`: configuracion e inyeccion de dependencias.

El flujo es `HTTP -> Controller -> Caso de uso -> Puerto -> Adaptador`. El adaptador
en memoria es el predeterminado. PostgreSQL puede activarse sin cambiar el dominio
ni los casos de uso.

## Requisitos

- Python 3.12 o superior (probado también con Python 3.14)
- PostgreSQL solo si se activa la persistencia SQL

## Instalacion y ejecucion

Desde la carpeta `SIPRIM_Agente`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn backend.main:app --reload
```

La API queda disponible en `http://127.0.0.1:8000`.
Los orígenes de desarrollo de React (`localhost:3000`) y Vite
(`localhost:5173`) están habilitados mediante `CORS_ORIGINS` en `.env`.

## Swagger

Abrir `http://127.0.0.1:8000/docs`, seleccionar
`POST /api/v1/proyectos`, pulsar **Try it out**, pegar el JSON de ejemplo y ejecutar.
Luego usar el `id` retornado en `GET /api/v1/proyectos/{proyecto_id}`.

JSON de ejemplo:

```json
{
  "nombre": "Mejoramiento de parque urbano",
  "descripcion": "Proyecto de recuperacion de espacio publico",
  "ubicacion": "El Tambo - Huancayo",
  "presupuesto": 2500000,
  "beneficiarios": 5000,
  "tipo_proyecto": "Infraestructura urbana"
}
```

## Llamadas de ejemplo

Registro con curl:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/proyectos \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Mejoramiento de parque urbano","descripcion":"Proyecto de recuperacion de espacio publico","ubicacion":"El Tambo - Huancayo","presupuesto":2500000,"beneficiarios":5000,"tipo_proyecto":"Infraestructura urbana"}'
```

Consulta y salud:

```bash
curl http://127.0.0.1:8000/api/v1/proyectos/1
curl http://127.0.0.1:8000/health
```

La respuesta de registro contiene el mensaje solicitado y el proyecto completo:

```json
{
  "mensaje": "Proyecto registrado correctamente",
  "proyecto": {
    "id": 1,
    "nombre": "Mejoramiento de parque urbano",
    "descripcion": "Proyecto de recuperacion de espacio publico",
    "ubicacion": "El Tambo - Huancayo",
    "presupuesto": 2500000.0,
    "beneficiarios": 5000,
    "tipo_proyecto": "Infraestructura urbana",
    "estado": "REGISTRADO",
    "fecha_creacion": "2026-09-18T23:00:00Z"
  }
}
```

## Pruebas

```powershell
pytest
```

Las pruebas cubren salud, registro, consulta, validaciones, proyecto inexistente y
el caso de uso aislado.

## Base de datos PostgreSQL

Scripts en [`database/`](database/). Conexión rápida con Docker:

```powershell
docker compose up -d db
Copy-Item .env.example .env   # si aún no tiene .env
python scripts/check_database.py
uvicorn backend.main:app --reload
```

En `.env`:

```dotenv
USE_IN_MEMORY_REPOSITORY=false
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/siprim
```

Para Neon/Supabase, pegue `database/schema.sql` en el SQL Editor y use su URL en
`DATABASE_URL` (prefijo `postgresql+psycopg://`).

`ProyectoRepositoryPort` desacopla la aplicacion de la base de datos. El frontend
solo consume la API; no necesita acceso directo a PostgreSQL.

## Frontend (React + Vite)

Interfaz PMV1 para la carga y consulta de expedientes (HU1.1).

```powershell
cd frontend
npm install
npm run dev
```

Abrir `http://localhost:5173` con el backend en `http://127.0.0.1:8000`.
En desarrollo, Vite redirige `/api` y `/health` al backend.

## Documentación

Los PDF y materiales de referencia del proyecto van en la carpeta [`docs/`](docs/).
Consulta [`docs/README.md`](docs/README.md) para el índice de archivos.
