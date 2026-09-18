import pytest
from app.infrastructure.config.settings import Settings
from app.infrastructure.output.ai.gemini_adapter import GeminiAdapter
from app.infrastructure.output.ai.openai_adapter import OpenAIAdapter
from app.infrastructure.output.ai.provider_factory import AIProviderFactory


def test_factory_gemini():
    service = AIProviderFactory.crear("gemini", Settings())
    assert isinstance(service, GeminiAdapter)


def test_factory_openai():
    service = AIProviderFactory.crear("openai", Settings())
    assert isinstance(service, OpenAIAdapter)


def test_factory_rechaza_proveedor_desconocido():
    with pytest.raises(ValueError):
        AIProviderFactory.crear("desconocido", Settings())
