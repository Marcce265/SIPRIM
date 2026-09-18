from abc import ABC, abstractmethod


class IRetrievalService(ABC):
    """Puerto para recuperación de normativa/documentos (RAG)."""

    @abstractmethod
    async def buscar(self, consulta: str, limite: int = 5) -> list[dict]:
        raise NotImplementedError
