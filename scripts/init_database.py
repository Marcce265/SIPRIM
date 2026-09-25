"""Crea tablas desde SQLAlchemy (alternativa a schema.sql)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.infrastructure.config.settings import get_settings
from backend.infrastructure.output.database.base import Base
from backend.infrastructure.output.database import models  # noqa: F401
from backend.infrastructure.output.database.session import engine


def main() -> int:
    settings = get_settings()
    if settings.use_in_memory_repository:
        print("USE_IN_MEMORY_REPOSITORY=true — no se aplicará esquema SQL.")
        return 1

    Base.metadata.create_all(bind=engine)
    print("Tablas creadas/verificadas con SQLAlchemy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
