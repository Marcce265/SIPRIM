"""Crea las tablas del PMV 1 en las tres bases y carga los datos semilla.

Uso:  python database/aplicar.py
Se puede ejecutar varias veces: no duplica tablas ni datos.
"""
from _comun import BASE, conectar

CARPETAS = {"auth": "auth_db", "platform": "platform_db", "economic": "economic_db"}

for nombre, carpeta in CARPETAS.items():
    with conectar(nombre) as conn:
        for archivo in ("01_schema.sql", "02_seed.sql", "03_comentarios.sql", "04_vistas_es.sql"):
            ruta = BASE / carpeta / archivo
            if ruta.exists():
                conn.execute(ruta.read_text(encoding="utf-8"))
        tablas = [r[0] for r in conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name")]
    print(f"[{carpeta}] Conexion OK -> {len(tablas)} tablas: {', '.join(tablas)}")
