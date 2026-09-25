from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.output.database.base import Base


class ProyectoModel(Base):
    """Modelo de persistencia separado de la entidad de dominio."""

    __tablename__ = "proyectos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    ubicacion: Mapped[str | None] = mapped_column(String(300), nullable=True)
    presupuesto: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    beneficiarios: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tipo_proyecto: Mapped[str | None] = mapped_column(String(150), nullable=True)
    estado: Mapped[str] = mapped_column(String(30), nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

