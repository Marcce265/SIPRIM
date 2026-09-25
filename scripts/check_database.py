"""Verifica conexión a PostgreSQL y existencia de tablas SIPRIM.

Uso (desde la raíz del repo):
    python scripts/check_database.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text

from backend.infrastructure.config.settings import get_settings


EXPECTED_TABLES = (
    "proyectos",
    "evaluaciones_economicas",
    "evaluaciones_juridicas",
)


def main() -> int:
    settings = get_settings()
    print(f"USE_IN_MEMORY_REPOSITORY = {settings.use_in_memory_repository}")
    print(f"DATABASE_URL = {settings.database_url.split('@')[-1] if '@' in settings.database_url else settings.database_url}")

    if settings.use_in_memory_repository:
        print("\nEl backend está en modo memoria. Cambie USE_IN_MEMORY_REPOSITORY=false en .env")
        return 1

    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            rows = conn.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name = ANY(:names)
                    ORDER BY table_name
                    """
                ),
                {"names": list(EXPECTED_TABLES)},
            ).fetchall()
    except Exception as exc:
        print(f"\nError de conexión: {exc}")
        print("\nSugerencia: docker compose up -d db")
        return 1

    found = {row[0] for row in rows}
    missing = [name for name in EXPECTED_TABLES if name not in found]

    print("\nConexión OK.")
    print(f"Tablas encontradas: {', '.join(sorted(found)) or '(ninguna)'}")

    if missing:
        print(f"Tablas faltantes: {', '.join(missing)}")
        print("Ejecute database/schema.sql en su instancia PostgreSQL.")
        return 1

    count = scalar(engine, "SELECT COUNT(*) FROM proyectos")
    print(f"Registros en proyectos: {count}")
    print("\nBase de datos lista para el backend.")
    return 0


def scalar(engine, sql: str) -> int:
    with engine.connect() as conn:
        return int(conn.execute(text(sql)).scalar_one())


if __name__ == "__main__":
    sys.exit(main())
