import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from google.genai import errors
from app.main import app
from app.infrastructure.input.controllers.evaluaciones import get_evaluar_proyecto


def test_endpoint_full_flow(monkeypatch, sdk, proyecto, dictamen):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')
    with TestClient(app) as client:
        response = client.post('/api/evaluaciones', json=proyecto)
    assert response.status_code == 200
    assert response.json() == dictamen
    sdk.generate.assert_awaited_once()


def test_missing_key(sdk, proyecto):
    with TestClient(app) as client:
        response = client.post('/api/evaluaciones', json=proyecto)
        assert client.get('/health').status_code == 200
    assert response.status_code == 503
    assert response.json()['detail']['code'] == 'IA_NOT_CONFIGURED'
    sdk.factory.assert_not_called()


@pytest.mark.parametrize('code,status', [(401,503),(403,503),(429,429),(500,502),(504,504)])
def test_errors_do_not_leak(monkeypatch, sdk, proyecto, code, status):
    monkeypatch.setenv('GEMINI_API_KEY', 'private-test-key')
    sdk.generate.side_effect = errors.APIError(code, {'error': {'message': 'private-test-key traceback'}})
    with TestClient(app) as client:
        response = client.post('/api/evaluaciones', json=proyecto)
        assert client.get('/health').status_code == 200
    assert response.status_code == status
    assert 'private-test-key' not in response.text
    assert 'traceback' not in response.text


@pytest.mark.parametrize('text,code', [('bad-json','IA_INVALID_RESPONSE'), ('','IA_EMPTY_RESPONSE')])
def test_bad_llm_output(monkeypatch, sdk, proyecto, text, code):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')
    sdk.generate.return_value = SimpleNamespace(text=text)
    response = TestClient(app).post('/api/evaluaciones', json=proyecto)
    assert response.status_code == 502
    assert response.json()['detail']['code'] == code


def test_internal_error_sanitized(proyecto):
    app.dependency_overrides[get_evaluar_proyecto] = lambda: SimpleNamespace(
        ejecutar=AsyncMock(side_effect=RuntimeError('secret traceback')))
    try:
        response = TestClient(app).post('/api/evaluaciones', json=proyecto)
        assert response.status_code == 500
        assert 'secret' not in response.text
    finally:
        app.dependency_overrides.clear()


def test_validation_and_registration(sdk, proyecto):
    with TestClient(app) as client:
        assert client.post('/api/evaluaciones', json={}).status_code == 422
        assert client.post('/api/evaluaciones', json={**proyecto, 'presupuesto': 'Infinity'}).status_code == 422
        registration = client.post('/api/proyectos', json=proyecto)
    assert registration.status_code == 201
    assert registration.json()['nombre'] == proyecto['nombre']
    sdk.generate.assert_not_called()


def test_swagger_and_openapi():
    with TestClient(app) as client:
        assert client.get('/docs').status_code == 200
        schema = client.get('/openapi.json').json()
    operation = schema['paths']['/api/evaluaciones']['post']
    assert operation['responses']['200']['content']['application/json']['schema']['$ref'].endswith('/DictamenIA')
    assert set(schema['components']['schemas']['DictamenIA']['required']) == {
        'puntaje', 'viabilidad', 'justificacion', 'observaciones', 'recomendaciones'}
