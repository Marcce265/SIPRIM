"""Utilidades compartidas: lee las URLs del .env y abre conexiones."""
import os
import sys
from pathlib import Path

import psycopg

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE = Path(__file__).parent
BASES = {"auth": "AUTH_DB_URL", "platform": "PLATFORM_DB_URL", "economic": "ECONOMIC_DB_URL"}


def url(nombre: str) -> str:
    valor = os.getenv(BASES[nombre])
    if not valor:
        sys.exit(f"Falta {BASES[nombre]} en el archivo .env")
    return valor.replace("postgresql+psycopg://", "postgresql://")


def conectar(nombre: str) -> psycopg.Connection:
    return psycopg.connect(url(nombre))
