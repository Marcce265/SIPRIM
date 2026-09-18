from abc import ABC, abstractmethod

from backend.domain.entities.proyecto import Proyecto


class ProyectoRepositoryPort(ABC):
    """Puerto de salida: el dominio no conoce donde se almacenan los proyectos."""

    @abstractmethod
    def guardar(self, proyecto: Proyecto) -> Proyecto:
        raise NotImplementedError

    @abstractmethod
    def obtener_por_id(self, proyecto_id: int) -> Proyecto | None:
        raise NotImplementedError

