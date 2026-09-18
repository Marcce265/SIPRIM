# SIPRIM: módulo de Integración IA/API (PMV1)

Evalúa una ficha de proyecto municipal y devuelve un `DictamenIA` validado:
`puntaje` (0–100), `viabilidad` (ALTA/MEDIA/BAJA), `justificacion`,
`observaciones` y `recomendaciones`. Es una evaluación preliminar de demostración,
no una aprobación oficial ni una validación del expediente.

## Arquitectura y flujo ejecutable

```text
POST /api/evaluaciones
  → EvaluarProyecto
  → AIEvaluationService
  → IIAService (puerto)
  → GeminiAdapter (infraestructura)
  → LangGraph: START → coordinador → tecnico → dictamen → END
  → DictamenIA → JSON REST
```

- `domain/ports/ia_service.py`: contrato abstracto, independiente del proveedor.
- `domain/value_objects/dictamen_ia.py`: modelo Pydantic v2; todos los campos son
  obligatorios, no permite campos extra, puntajes fuera del rango ni no finitos.
- `application`: caso de uso y servicio dependen del puerto, sin SDK ni LangGraph.
  El esquema anterior se conserva como reexportación para no romper imports.
- `infrastructure/output/ai/gemini_adapter.py`: implementa el puerto, ejecuta el
  grafo y realiza la llamada asíncrona con el SDK oficial `google-genai`.
- `app/ai`: detalle de orquestación usado solo desde infraestructura. Estado
  `EvaluationState` tipado; la llamada LLM ocurre dentro del nodo `dictamen`.
- `infrastructure/input/controllers/evaluaciones.py`: ensambla dependencias con
  FastAPI y traduce errores a respuestas controladas sin publicar excepciones.

El dominio no importa FastAPI, Gemini, LangGraph, Qdrant ni SQLAlchemy. La aplicación
no importa infraestructura. Otro proveedor podría implementar `IIAService`.
Se retiraron la fábrica y el fallback porque hay un solo proveedor.

## Agentes implementados y pendientes

| Nodo | Implementación PMV1 |
|---|---|
| Coordinador | Comprueba la ficha mínima y delimita el alcance técnico preliminar. |
| Técnico | Comprueba magnitudes positivas, calcula costo por beneficiario y explicita evidencias faltantes. |
| Dictamen | Una llamada Gemini con contexto de ambos nodos, JSON Schema y validación Pydantic. |
| Económico, Jurídico, Social, Ambiental | Archivos de estructura reservados; no se ejecutan ni se presentan como implementados. |

Coordinador y Técnico son nodos deterministas, no dos LLM independientes. La
interpretación generativa ocurre en la consolidación. El prompt usa una rúbrica
**provisional de demostración**, no una metodología municipal validada: coherencia
0–40, claridad del alcance/beneficiarios 0–30 y sustento técnico 0–30. Pide justificar
los componentes; ALTA >=70, MEDIA >=40, BAJA <40. Los límites y tipos se validan en
código; la veracidad de la justificación y su rúbrica aún requieren revisión humana.

## Modelo, SDK y costo

Modelo predeterminado: **`gemini-2.5-flash`**. Se seleccionó porque la documentación
oficial lo muestra con API de generación estructurada y Free Tier para entrada y
salida, adecuado para una demostración universitaria. Se mantiene configurable
mediante `AI_MODEL`. SDK oficial: `google-genai==1.75.0`.

Cada evaluación hace una sola llamada `client.aio.models.generate_content`, con
`response_mime_type="application/json"` y `response_json_schema`. Se valida también
el texto devuelto, no se confía únicamente en el formato solicitado. El cliente
asíncrono se cierra al terminar. Se limita el tiempo total del grafo y el timeout HTTP;
se desactivan los reintentos automáticos (`attempts=1`).

Para una demostración sin pagos, usar un proyecto de Google AI Studio en Free Tier,
sin activar facturación. La cuota, disponibilidad regional y acceso al modelo dependen
de Google y de la cuenta: gratuito no significa ilimitado. Un 429 devuelve un error;
no cambia a un proveedor o plan de pago. El programa no puede verificar el plan de
facturación asociado a una clave. Usar datos ficticios para la demo; Google indica
que los datos del Free Tier pueden utilizarse para mejorar sus productos.

Documentación oficial consultada el 18/09/2026:

- [SDK Python: generación, JSON Schema y cierre asíncrono](https://googleapis.github.io/python-genai/)
- [Salidas estructuradas](https://ai.google.dev/gemini-api/docs/structured-output)
- [Precios y Free Tier](https://ai.google.dev/gemini-api/docs/pricing)
- [Crear y configurar una API key](https://ai.google.dev/gemini-api/docs/api-key)
- [Cuotas vigentes de la cuenta](https://ai.google.dev/gemini-api/docs/rate-limits)

## Configuración e instalación (Python 3.12)

Desde la raíz del repositorio, en **Windows PowerShell**:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

En **Linux/macOS**:

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Obtener la clave en [Google AI Studio](https://aistudio.google.com/apikey), seleccionar
un proyecto con Free Tier y pegarla **solo en el archivo local `.env`**. No enviar
la clave por chat, incluirla en capturas ni subirla al repositorio.

| Variable | Valor / propósito |
|---|---|
| `GEMINI_API_KEY` | Clave local. Vacía en `.env.example`; obligatoria solo al evaluar. |
| `AI_MODEL` | `gemini-2.5-flash` por defecto. |
| `APP_ENV` | `development` por defecto. |
| `AI_TIMEOUT_SECONDS` | `45` por defecto; mayor que 0 y máximo 120. |
| `DATABASE_URL` | Se conserva para futura persistencia; no se usa en esta evaluación. |
| `QDRANT_URL`, `QDRANT_API_KEY` | Reservadas para RAG, no se requieren para PMV1. |

`pydantic-settings` carga `backend/.env` incluso si cambia el directorio de trabajo;
las variables del proceso tienen prioridad. Reiniciar FastAPI tras cambiar configuración.
Las claves se representan con `SecretStr`. `.gitignore` excluye `.env`; `.dockerignore`
impide incorporarlo a la imagen. No se crea ningún archivo con claves reales.

## Arrancar FastAPI y abrir Swagger

Windows:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Linux/macOS:

```bash
.venv/bin/python -m uvicorn app.main:app --reload
```

Abrir [Swagger](http://127.0.0.1:8000/docs),
[health](http://127.0.0.1:8000/health) o
[OpenAPI](http://127.0.0.1:8000/openapi.json).

| Endpoint | Comportamiento |
|---|---|
| `GET /health` | `{"status":"ok"}`; no verifica credenciales ni consume Gemini. |
| `POST /api/evaluaciones` | Recibe la ficha completa y ejecuta la evaluación real. |
| `POST /api/proyectos` | Contrato existente: devuelve ficha e ID secuencial temporal. No almacena ni recupera proyectos. |

Se conserva el endpoint equivalente existente `/api/evaluaciones`. No se añade
`/api/proyectos/{id}/evaluar` porque aún no existe un repositorio capaz de recuperar
el proyecto por ID. No es necesario registrar un proyecto antes de evaluarlo.
Esto evita simular persistencia o intervenir en el módulo del compañero.

Con Docker: `docker compose up --build api`. PostgreSQL y Qdrant están en perfiles
opcionales `persistence` y `rag`; el PMV no los necesita. El contenedor recibe `.env`
en tiempo de ejecución mediante `env_file`, no lo incorpora a la imagen.

## Petición y respuesta

En Swagger: `POST /api/evaluaciones` → **Try it out** → pegar este JSON → **Execute**:

```json
{
  "nombre": "Mejoramiento de agua potable",
  "descripcion": "Ampliar la red de agua potable para familias del distrito.",
  "presupuesto": 100000,
  "poblacion_beneficiaria": 200,
  "distrito": "Huancayo"
}
```

Respuesta **ilustrativa**, no resultado garantizado ni obtenido de una llamada real:

```json
{
  "puntaje": 65.0,
  "viabilidad": "MEDIA",
  "justificacion": "Coherencia: 30/40; alcance: 25/30; sustento: 10/30. Total: 65/100. La ficha permite una evaluación preliminar, pero falta evidencia técnica.",
  "observaciones": ["Falta expediente técnico y cronograma."],
  "recomendaciones": ["Validar costos unitarios y alcance con el área técnica."]
}
```

Los valores varían según la ficha y el modelo. El costo por beneficiario no demuestra
rentabilidad ni suficiencia presupuestal.

## Errores controlados

Formato: `{"detail":{"code":"IA_NOT_CONFIGURED","message":"El servicio IA no está configurado."}}`.

| HTTP | Código / condición |
|---|---|
| 422 | Ficha de entrada inválida (FastAPI/Pydantic). |
| 503 | `IA_NOT_CONFIGURED`, `IA_AUTH_ERROR`: falta clave o Google la rechaza. |
| 429 | `IA_RATE_LIMIT`: cuota agotada. |
| 504 | `IA_TIMEOUT`: timeout HTTP o del flujo completo. |
| 502 | `IA_PROVIDER_ERROR`, `IA_INVALID_RESPONSE`, `IA_EMPTY_RESPONSE`. |
| 500 | `IA_GRAPH_ERROR` o `IA_INTERNAL_ERROR`: fallo interno controlado. |

Una clave inválida puede llegar como 400 `API_KEY_INVALID`, 401 o 403; se traduce a
503 porque las credenciales son del servidor. No se devuelve el texto de excepciones,
claves ni stack traces. FastAPI sigue atendiendo `/health` tras un error de evaluación.

## Pruebas sin consumir API

Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Linux/macOS:

```bash
.venv/bin/python -m pytest -q
```

Con el entorno activado también funciona `pytest`. La suite bloquea conexiones de
red, utiliza una clave ficticia y mocks/fakes. Incluye adaptador, configuración,
respuesta válida/inválida/vacía, errores SDK, timeout, grafo real y orden de nodos,
caso de uso, límites arquitectónicos, endpoint completo, health y Swagger. Una prueba
adicional usa el SDK real con `httpx.MockTransport` para comprobar serialización del
JSON Schema y procesamiento HTTP sin contactar a Google.

## PMV2 / PMV3 y límites actuales

- Conectar PostgreSQL mediante un puerto de repositorio y evaluar por ID persistido.
- Implementar los agentes Económico, Jurídico, Social y Ambiental.
- Desarrollar RAG/corpus normativo: `IRetrievalService` y `QdrantAdapter` quedan como
  estructura; el stub no recupera evidencia y no participa en el flujo.
- Acordar y validar la rúbrica municipal y sus ponderaciones con el grupo/docente.
- Incorporar revisión humana, trazabilidad, autenticación, autorización y checkpoints.
- Colas y escalamiento solo cuando el flujo lo requiera.

No se instalaron SQLAlchemy, Alembic, psycopg ni qdrant-client porque aún no se usan.
Reincorporarlos al implementar persistencia/RAG. Las versiones directas están fijadas
a las utilizadas en pruebas; las dependencias transitivas no constituyen un lockfile.
El servidor es una demo local, todavía no un servicio listo para exposición pública.
La integración con una clave real requiere la prueba manual anterior: los tests
verifican contratos y errores, no la cuota ni las credenciales de una cuenta Google.

## Validación de esta entrega

Ejecutada con Python 3.12.14: `pytest -q` → **48 passed, 0 failed**.
Dos avisos de deprecación provienen de Starlette/AnyIO y LangGraph/LangChain;
no afectan el resultado. `pip check` no detectó dependencias incompatibles;
`compileall` e imports de la aplicación completaron correctamente. Uvicorn arrancó
como proceso real y `/health`, `/docs` y `/openapi.json` respondieron HTTP 200.
`git diff --check` no detectó errores de espacios; `.env` y variantes se ignoran.
No se encontraron patrones de claves reales en los archivos revisados ni referencias
al proveedor retirado. No se hizo una llamada a Google con credenciales reales.
