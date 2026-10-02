# SIPRIM Frontend

Interfaz web del PMV1 (React 19 + Vite + TypeScript).

**Enfoque del equipo:** el contrato y la lógica viven en el **backend** (`/api/v1`, auth_db, etc.).
Este frontend **solo se adapta** a esa API (proxy, JWT, roles, timeouts y mensajes al usuario).
No se modifican servicios Python salvo acuerdo explícito con backend.

API de desarrollo: **http://127.0.0.1:8000**

## Desarrollo

```powershell
npm install
npm run dev
```

Abrir `http://localhost:5173`. Vite envía `/api` y `/health` a `http://127.0.0.1:8000`.

### Backend requerido (puerto 8000)

Opción A — API local:

```powershell
cd ..   # raíz del repo
docker compose up -d postgres redis
.\.venv\Scripts\activate
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Opción B — API en Docker (mismo puerto 8000 en el host):

```powershell
cd ..   # raíz del repo
docker compose up -d --build
```

Compruebe: `http://127.0.0.1:8000/health` debe responder `{"status":"ok"}`.

Si el login devuelve **500**, suele faltar `auth_db` en Postgres (contenedor antiguo). Desde la raíz del repo: `python database/ensure_pm_v1.py` y reinicie la API.

No defina `VITE_API_BASE_URL` en desarrollo salvo despliegue separado; el proxy de Vite ya apunta a 8000.

## Scripts

| Comando | Descripción |
|---------|-------------|
| `npm run dev` | Puerto 5173, proxy `/api` → `8000` |
| `npm run build` | Compilación de producción |
| `npm run lint` | Oxlint |

## Producción

Defina `VITE_API_BASE_URL` con la URL pública del API si el front no usa el proxy de Vite.
