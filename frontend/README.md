# SIPRIM Frontend

Interfaz web del PMV1 (React 19 + Vite + TypeScript).

**Enfoque:** el contrato y la lógica viven en el **backend** (`/api/v1`, auth_db, etc.).
Este frontend **solo se adapta** a esa API (proxy, JWT, roles, timeouts y mensajes al usuario).

API de desarrollo: **http://127.0.0.1:8000**

## Desarrollo

```powershell
npm install
npm run dev
```

Abrir `http://localhost:5173`. Vite envía `/api` y `/health` a `http://127.0.0.1:8000`.

### Backend requerido (puerto 8000)

```powershell
cd ..   # raíz del repo
docker compose up -d postgres redis api
# o: uvicorn local (ver README raíz)
```

Compruebe: `http://127.0.0.1:8000/health` → `{"status":"ok"}`.

Si el login devuelve **500**, ejecute en la raíz: `python database/ensure_pm_v1.py` y reinicie la API.

No defina `VITE_API_BASE_URL` en desarrollo salvo despliegue separado.

## Rutas principales

| Ruta | Descripción |
|------|-------------|
| `/login` | Autenticación JWT |
| `/registrar` | `POST /api/v1/projects` |
| `/consultar` | `GET /api/v1/projects/{uuid}` |
| `/proyectos/:id` | Validación, evaluación, prechecks |
| `/normativa` | Búsqueda RAG (rol `LEGAL_ADVISOR`) |
| `/proyectos/:id/aprobacion` | Dictamen humano (rol `ADMIN`) |

La carpeta `src/simulation/` queda del merge con demo local; el flujo oficial usa la API anterior.

## Scripts

| Comando | Descripción |
|---------|-------------|
| `npm run dev` | Puerto 5173, proxy `/api` → `8000` |
| `npm run build` | Compilación de producción |
| `npm run lint` | Oxlint |

## Producción

Defina `VITE_API_BASE_URL` con la URL pública del API si el front no usa el proxy de Vite.
