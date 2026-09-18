import json
import socket
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.infrastructure.config.settings import get_settings


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', '')
    monkeypatch.setenv('LANGSMITH_TRACING', 'false')
    monkeypatch.setenv('LANGCHAIN_TRACING_V2', 'false')
    def denied(*args, **kwargs):
        raise AssertionError('Network disabled in tests')
    monkeypatch.setattr(socket.socket, 'connect', denied)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def proyecto():
    return dict(nombre='Agua potable', descripcion='Mejorar acceso al agua potable.',
                presupuesto=100000, poblacion_beneficiaria=200, distrito='Huancayo')


@pytest.fixture
def dictamen():
    return dict(puntaje=65.0, viabilidad='MEDIA',
                justificacion='Evaluación preliminar; falta sustento documental.',
                observaciones=['Falta expediente técnico.'],
                recomendaciones=['Validar costos y cronograma.'])


@pytest.fixture
def sdk(monkeypatch, dictamen):
    client = SimpleNamespace(models=SimpleNamespace(
        generate_content=AsyncMock(return_value=SimpleNamespace(text=json.dumps(dictamen)))))
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=client)
    context.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=SimpleNamespace(aio=context))
    monkeypatch.setattr('app.infrastructure.output.ai.gemini_adapter.genai.Client', factory)
    return SimpleNamespace(factory=factory, generate=client.models.generate_content, context=context)
