# SIPRIM — backend e infraestructura PMV1

Prototipo academico para registrar expedientes municipales y ejecutar una
preevaluacion explicable. Las fuentes principales de producto son el documento
maestro y el modelo de tres bases del PMV1. El estado comprobado de las cuatro
capacidades heredadas se encuentra en
[`docs/REVISION_HISTORIAS_BACKEND_PMV1.md`](docs/REVISION_HISTORIAS_BACKEND_PMV1.md).

## Arquitectura

Se usa arquitectura hexagonal (puertos y adaptadores):

- `domain`: entidad `Proyecto`, estado, reglas y puerto del repositorio. No depende
  de FastAPI, Pydantic ni SQLAlchemy.
- `application`: DTOs, casos de uso y servicios de aplicacion del PMV1.
- `infrastructure/input`: controladores REST de FastAPI.
- `infrastructure/output`: repositorio en memoria y adaptador SQLAlchemy.
- `infrastructure/config`: configuracion e inyeccion de dependencias.

El flujo oficial es `HTTP -> servicio de aplicacion -> platform_db/outbox ->
Celery/Redis -> worker economico -> economic_db -> evento completado ->
platform_db`. Los endpoints heredados en espanol siguen disponibles para no
romper el frontend existente, pero la ruta oficial usa UUID y las tres bases.

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

La ruta oficial `POST /api/v1/projects` usa además `location` y
`proposed_land_use`. Ambos datos son obligatorios para abrir la prevalidación
territorial de HU1.11.

## Integracion IA/API con Gemini

El aporte de integracion IA agrega un dictamen preliminar sobre los proyectos ya
registrados, sin reemplazar los casos de uso economico o juridico existentes. El
flujo conserva la arquitectura hexagonal del proyecto:

```text
POST /api/v1/proyectos/{id}/evaluacion-ia
  -> EvaluarProyectoIAUseCase
  -> IAServicePort
  -> GeminiAdapter
  -> LangGraph: coordinador -> tecnico -> dictamen
  -> DictamenIAResponse
```

La ficha debe estar completa. El resultado incluye `puntaje` (0-100), `viabilidad`
(`ALTA`, `MEDIA` o `BAJA`), `justificacion`, `observaciones` y `recomendaciones`.
Es una evaluacion orientativa y no constituye aprobacion municipal.

En `.env` configurar:

```dotenv
GEMINI_API_KEY=clave_de_google_ai_studio
AI_MODEL=gemini-2.5-flash
AI_TIMEOUT_SECONDS=45
```

La clave no se almacena en Git. En un despliegue debe registrarse como variable
privada del servicio. Para probar en Swagger: registrar un proyecto completo, copiar
su `id` y ejecutar `POST /api/v1/proyectos/{id}/evaluacion-ia`.

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

Las pruebas cubren salud, registro, consulta, campos faltantes, puntuacion
economica documentada, abstencion juridica y el adaptador opcional de IA.

## Base de datos PostgreSQL

Scripts en [`database/`](database/). La infraestructura oficial del PMV1 usa
tres bases logicas con propietarios separados dentro de una instancia PostgreSQL,
mas Redis como broker. Conexion rapida con Docker:

```powershell
docker compose up -d --build
Copy-Item .env.example .env   # si aún no tiene .env
python database/verificar.py
```

Con Docker, la API queda en `http://127.0.0.1:8001` por defecto para evitar
conflictos con servidores locales que usan `8000`. Puede cambiarse mediante
`API_PORT` en `.env`. La ejecución directa con Uvicorn conserva el puerto 8000.

En `.env`:

```dotenv
USE_IN_MEMORY_REPOSITORY=false
AUTH_DB_URL=postgresql+psycopg://auth_app:auth_dev_only@localhost:5432/auth_db
PLATFORM_DB_URL=postgresql+psycopg://platform_app:platform_dev_only@localhost:5432/platform_db
ECONOMIC_DB_URL=postgresql+psycopg://economic_app:economic_dev_only@localhost:5432/economic_db
```

`database/schema.sql` pertenece al adaptador heredado y no sustituye los esquemas
oficiales de `auth_db`, `platform_db` y `economic_db`.

Las cuentas ficticias locales son `planner@siprim.test`, `admin@siprim.test` y
`legal@siprim.test`, todas con `Prueba2026!`. No deben utilizarse fuera de desarrollo.

Recorrido principal:

1. `POST /api/v1/auth/login` obtiene el token del planificador, asesor jurídico o administrador.
2. `POST /api/v1/projects` registra proyecto y version en `platform_db`.
3. `POST /api/v1/evaluations` requiere `Idempotency-Key` y responde `202 queued`.
4. `GET /api/v1/evaluations/{id}` expone el avance y el resultado explicable.
5. `POST /api/v1/projects/{id}/zoning-precheck`, con `Idempotency-Key`, registra
   la prevalidación de zonificación.
6. `POST /api/v1/normative/search`, con `Idempotency-Key` y rol `LEGAL_ADVISOR` o `ADMIN`,
   busca citas normativas con texto legal real y detecta alertas jurídicas (HU2.1).
   `GET /api/v1/normative/documents` lista el catálogo normativo oficial disponible.
7. `POST /api/v1/projects/{id}/approval`, con `Idempotency-Key` y rol `ADMIN`, emite
   el dictamen humano formal (`approved`, `rejected` u `observed`), compuerta final
   del PMV1 tras completar la evaluación técnica.
   `GET /api/v1/projects/{id}/approval` consulta el estado de la compuerta humana.

HU1.11 no declara compatibilidad PDU/PDM si no existe evidencia territorial
versionada. En el alcance actual devuelve `compatible=null`, una alerta y
`requires_human_review=true`. Una conclusión futura deberá incluir documento,
versión, localizador y fragmento verificable.

HU2.1 no emite dictámenes jurídicos concluyentes de forma autónoma. Recupera citas
con texto legal real y trazabilidad completa (documento, versión, artículo, localizador y fragmento)
y marca alertas para revisión humana obligatoria (`requires_human_review=true`).

Compuerta de Aprobación Humana: Ningún proyecto se considera concluido o dictaminado
de forma puramente automática. Una vez procesadas las evaluaciones técnicas (económica,
territorial y normativa), se exige la intervención de un usuario con rol `ADMIN` que emite
un dictamen formal con justificación obligatoria y condiciones registradas (en caso de observación).

El frontend solo consume la API; no necesita ni debe tener acceso directo a
PostgreSQL.

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
