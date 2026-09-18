from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.infrastructure.config.settings import get_settings


settings = get_settings()

# create_engine no abre una conexion hasta que una sesion ejecuta una operacion.
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

