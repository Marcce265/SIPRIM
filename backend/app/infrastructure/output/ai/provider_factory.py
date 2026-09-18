from app.domain.ports.ia_service import IIAService
from app.infrastructure.config.settings import Settings
from app.infrastructure.output.ai.gemini_adapter import GeminiAdapter
from app.infrastructure.output.ai.openai_adapter import OpenAIAdapter


class AIProviderFactory:
    @staticmethod
    def crear(nombre: str, settings: Settings) -> IIAService:
        proveedor = nombre.strip().lower()
        if proveedor == "gemini":
            return GeminiAdapter(settings.gemini_api_key, settings.gemini_model)
        if proveedor == "openai":
            return OpenAIAdapter(settings.openai_api_key, settings.openai_model)
        raise ValueError(f"Proveedor IA no soportado: {nombre}")
