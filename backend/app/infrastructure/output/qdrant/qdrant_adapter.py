from app.domain.ports.retrieval_service import IRetrievalService


class QdrantAdapter(IRetrievalService):
    """Stub preparado para PMV2: RAG sobre normativa municipal."""

    async def buscar(self, consulta: str, limite: int = 5) -> list[dict]:
        return []
