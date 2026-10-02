# Bases de datos del PMV 1

La infraestructura local implementa las tres bases logicas definidas por el
modelo maestro. Las tres viven en una sola instancia PostgreSQL, pero cada una
tiene propietario y credenciales de aplicacion independientes:

- `auth_db` / `auth_app`
- `platform_db` / `platform_app`
- `economic_db` / `economic_app`

Redis funciona como broker y no es fuente de verdad.

## Inicio local

```powershell
docker compose up -d postgres redis
Copy-Item database/.env.example .env
```

La primera inicializacion aplica, en orden, los archivos `01_schema.sql`,
`02_seed.sql`, `03_comentarios.sql` y `04_vistas_es.sql` de cada base. Para
reaplicar de forma idempotente sobre bases ya existentes:

```powershell
python database/aplicar.py
```

Para demostrar el contrato de evaluacion economica y la idempotencia sin
depender todavia del worker Celery:

```powershell
python database/simular_flujo.py
python database/simular_flujo.py --duplicar
python database/verificar.py
```

Las contrasenas incluidas son exclusivamente de desarrollo local. No deben
usarse en un despliegue ni copiarse a servicios externos.
