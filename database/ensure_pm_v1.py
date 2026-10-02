"""Crea auth_db / platform_db / economic_db y aplica SQL PMV1 sobre Postgres local (Docker).

Uso (Postgres en localhost:5432, usuario postgres/postgres):

    python database/ensure_pm_v1.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import psycopg
import psycopg.sql

BASE = Path(__file__).parent
SUPERUSER_URL = "postgresql://postgres:postgres@127.0.0.1:5432/postgres"

ROLES = (
    ("auth_app", "auth_dev_only"),
    ("platform_app", "platform_dev_only"),
    ("economic_app", "economic_dev_only"),
)
DATABASES = (
    ("auth_db", "auth_app", "auth_db"),
    ("platform_db", "platform_app", "platform_db"),
    ("economic_db", "economic_app", "economic_db"),
)
PERMISOS = (
    ("auth_db", "01_auth_db.sql"),
    ("platform_db", "02_platform_db.sql"),
    ("economic_db", "03_economic_db.sql"),
)


def main() -> int:
    passwords = dict(ROLES)

    with psycopg.connect(SUPERUSER_URL, autocommit=True) as conn:
        for role, password in ROLES:
            exists = conn.execute(
                "SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)
            ).fetchone()
            if not exists:
                conn.execute(
                    psycopg.sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                        psycopg.sql.Identifier(role),
                        psycopg.sql.Literal(password),
                    )
                )
                print(f"Rol creado: {role}")

        for db_name, owner, _folder in DATABASES:
            exists = conn.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (db_name,)
            ).fetchone()
            if not exists:
                conn.execute(
                    psycopg.sql.SQL("CREATE DATABASE {} OWNER {}").format(
                        psycopg.sql.Identifier(db_name),
                        psycopg.sql.Identifier(owner),
                    )
                )
                print(f"Base creada: {db_name}")

    for db_name, owner, folder in DATABASES:
        app_url = f"postgresql://{owner}:{passwords[owner]}@127.0.0.1:5432/{db_name}"
        with psycopg.connect(app_url, autocommit=True) as conn:
            for sql_file in sorted((BASE / folder).glob("*.sql")):
                conn.execute(sql_file.read_text(encoding="utf-8"))
                print(f"Aplicado {sql_file.name} -> {db_name}")

    for db_name, perm_file in PERMISOS:
        perm_path = BASE / "permisos" / perm_file
        if not perm_path.exists():
            continue
        db_url = f"postgresql://postgres:postgres@127.0.0.1:5432/{db_name}"
        with psycopg.connect(db_url, autocommit=True) as conn:
            conn.execute(perm_path.read_text(encoding="utf-8"))
            print(f"Permisos: {perm_file}")

    print("PMV1 listo. Ejecute: python database/verificar.py")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except psycopg.Error as exc:
        print(f"Error PostgreSQL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
