# SIPRIM Frontend

Interfaz web del PMV1 (React 19 + Vite + TypeScript).

## Desarrollo

```powershell
npm install
npm run dev
```

Requisito: backend FastAPI en `http://127.0.0.1:8000` (`uvicorn backend.main:app --reload` desde la raíz del repo).

## Estructura del código

```
src/
├── app/                    # Arranque y rutas
│   ├── App.tsx
│   └── routes.tsx
├── api/                    # Capa HTTP
│   ├── client.ts           # fetch base y errores
│   └── proyectos.api.ts    # endpoints de proyectos
├── components/
│   ├── layout/             # Layout, ApiStatusPill
│   ├── proyecto/           # ProyectoCard
│   ├── roadmap/            # RoadmapPanel + constantes PMV1
│   └── ui/                 # Alert, FormField, PageHeader
├── features/               # Pantallas por historia de usuario
│   ├── home/
│   ├── registrar/          # HU1.1 — formulario, validación, hook
│   └── consultar/
├── hooks/
│   └── useApiHealth.ts
├── styles/                 # Tokens y estilos globales
│   ├── tokens.css          # Colores y variables SIPRIM
│   ├── global.css
│   ├── forms.css
│   └── index.css           # punto de entrada de estilos
├── types/
│   └── proyecto.ts
└── utils/
    ├── format.ts
    └── recentProjects.ts
```

### Convenciones

- **Páginas delgadas** en `features/*/`: componen UI y delegan lógica a hooks.
- **Validación** alineada con Pydantic del backend en `features/registrar/validateProyecto.ts`.
- **API** centralizada: no usar `fetch` directo en componentes.
- **Estilos**: tokens en `styles/tokens.css`; clases reutilizables en `global.css`, `forms.css`, etc.

## Pantallas

| Ruta | Feature | Descripción |
|------|---------|-------------|
| `/` | `home` | Inicio, hoja de ruta y expedientes recientes (localStorage) |
| `/registrar` | `registrar` | Carga de expediente HU1.1 / RF-01 |
| `/consultar` | `consultar` | Detalle por ID de expediente |

## Scripts

| Comando | Descripción |
|---------|-------------|
| `npm run dev` | Servidor de desarrollo (puerto 5173, proxy al API) |
| `npm run build` | Compilación de producción |
| `npm run lint` | Oxlint |
| `npm run preview` | Vista previa del build |

## Producción

Defina `VITE_API_BASE_URL` apuntando al backend si no usa el proxy de Vite.
