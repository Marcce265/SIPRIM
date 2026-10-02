# SIPRIM Frontend

Simulación funcional del PMV 1 (React 19 + Vite + TypeScript). Ejecuta el agente
económico en el navegador y persiste los datos ficticios en `localStorage`.

## Desarrollo

```powershell
npm install
npm run dev
```

No requiere backend, base de datos, broker ni proveedor LLM.

## Estructura del código

```
src/
├── app/                    # Arranque y rutas
│   ├── App.tsx
│   └── routes.tsx
├── api/                    # Adaptador HTTP heredado, aislado de la demo
├── components/
│   ├── layout/             # Layout, ApiStatusPill
│   ├── proyecto/           # ProyectoCard
│   ├── roadmap/            # RoadmapPanel + constantes PMV1
│   └── ui/                 # Alert, FormField, PageHeader
├── features/               # Inicio, proyectos, registro, criterios y acceso
├── simulation/             # Repositorio local y agente económico independiente
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
- **Datos de demostración** centralizados: los componentes solo usan el repositorio de `simulation/`.
- **Integración HTTP** aislada: no se mezcla con el estado local del PMV 1.
- **Estilos**: tokens en `styles/tokens.css`; clases reutilizables en `global.css`, `forms.css`, etc.

## Pantallas

| Ruta | Feature | Descripción |
|------|---------|-------------|
| `/login` | `auth` | Selección de perfil de demostración |
| `/` | `home` | Resumen de alcance y estado local |
| `/proyectos` | `projects` | Listado persistente y adaptable |
| `/proyectos/nuevo` | `registrar` | Alta con validación (Planificador) |
| `/proyectos/:id` | `projects` | Detalle, evaluaciones y versiones |
| `/proyectos/:id/editar` | `projects` | Edición/versionado (Planificador) |
| `/criterios` | `criteria` | Umbrales versionados (Administrador) |

### Perfiles de demostración

- `planificador@siprim.demo` / `demo2026`
- `admin@siprim.demo` / `demo2026`

Los perfiles sirven para demostrar visibilidad y acciones por rol. No son autorización
de servidor. `localStorage` conserva solo el identificador de la sesión y los datos del
proyecto; no guarda contraseñas ni tokens.

## Recorrido de demostración

1. Entre como Planificador y compruebe los proyectos A y B. Sus resultados son S/ 200
   y 100 puntos; S/ 300 y 66,67 puntos, respectivamente.
2. Registre un proyecto y valide presupuesto negativo o beneficiarios cero.
3. Inicie la evaluación y observe `pendiente → procesando → completado`. Use “Simular
   fallo técnico” para comprobar `fallido` y luego reintente.
4. Edite un proyecto evaluado: se crea una versión nueva y el resultado previo permanece.
5. Recargue el navegador y verifique que los datos continúan.
6. Entre como Administrador, active otros umbrales y vuelva como Planificador. Una nueva
   evaluación usa la configuración nueva sin modificar las anteriores.
7. Use “Restaurar datos iniciales”; la aplicación pide confirmación antes de borrar cambios.

## Scripts

| Comando | Descripción |
|---------|-------------|
| `npm run dev` | Servidor de desarrollo (puerto 5173, proxy al API) |
| `npm run typecheck` | Comprobación estática de TypeScript |
| `npm run build` | Compilación de producción |
| `npm run lint` | Oxlint |
| `npm run preview` | Vista previa del build |

## Producción

Defina `VITE_API_BASE_URL` apuntando al backend si no usa el proxy de Vite.
