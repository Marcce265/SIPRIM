import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import httpx
import pytest
from google.genai import errors
from app.domain.errors import (
    IAConfigurationError, IAAuthenticationError, IATimeoutError, IARateLimitError,
    IAProviderError, IAInvalidResponseError, IAEmptyResponseError, IAGraphError,
)
from app.infrastructure.output.ai.gemini_adapter import GeminiAdapter


async def test_valid_response_and_schema(sdk, proyecto, dictamen):
    result = await GeminiAdapter('test-key', 'gemini-2.5-flash').generar_dictamen(proyecto)
    assert result.model_dump() == dictamen
    sdk.generate.assert_awaited_once()
    args = sdk.generate.call_args.kwargs
    assert args['model'] == 'gemini-2.5-flash'
    assert args['config'].response_mime_type == 'application/json'
    assert set(args['config'].response_json_schema['required']) == set(dictamen)
    context = json.loads(args['contents'])
    assert context['proyecto'] == proyecto
    assert '500.00' in context['analisis_tecnico']
    assert 'preliminar' in context['analisis_coordinador']
    sdk.context.__aexit__.assert_awaited_once()
    assert sdk.factory.call_args.kwargs['http_options'].retry_options.attempts == 1


@pytest.mark.parametrize('key', [None, '', '   '])
async def test_missing_key(sdk, proyecto, key):
    with pytest.raises(IAConfigurationError):
        await GeminiAdapter(key, 'gemini-2.5-flash').generar_dictamen(proyecto)
    sdk.factory.assert_not_called()


@pytest.mark.parametrize('text', ['not-json', '{}', 'null', '[]',
    '{"puntaje": 101, "viabilidad": "ALTA", "justificacion": "Suficiente texto", "observaciones": [], "recomendaciones": []}',
    '{"puntaje": "80", "viabilidad": "ALTA", "justificacion": "Suficiente texto", "observaciones": [], "recomendaciones": []}'])
async def test_invalid_response(sdk, proyecto, text):
    sdk.generate.return_value = SimpleNamespace(text=text)
    with pytest.raises(IAInvalidResponseError):
        await GeminiAdapter('test', 'gemini-2.5-flash').generar_dictamen(proyecto)


@pytest.mark.parametrize('text', [None, '', '  '])
async def test_empty_response(sdk, proyecto, text):
    sdk.generate.return_value = SimpleNamespace(text=text)
    with pytest.raises(IAEmptyResponseError):
        await GeminiAdapter('test', 'gemini-2.5-flash').generar_dictamen(proyecto)


@pytest.mark.parametrize('code,reason,expected', [
    (400, 'API_KEY_INVALID', IAAuthenticationError),
    (401, '', IAAuthenticationError), (403, '', IAAuthenticationError),
    (429, '', IARateLimitError), (500, '', IAProviderError),
    (400, '', IAProviderError), (404, '', IAProviderError),
    (408, '', IATimeoutError), (504, '', IATimeoutError),
])
async def test_provider_errors(sdk, proyecto, code, reason, expected):
    sdk.generate.side_effect = errors.APIError(code, {'error': {
        'message': 'secret-key-and-internal-details', 'details': [{'reason': reason}]}})
    with pytest.raises(expected) as exc:
        await GeminiAdapter('test', 'gemini-2.5-flash').generar_dictamen(proyecto)
    assert 'secret-key' not in str(exc.value)
    sdk.context.__aexit__.assert_awaited_once()


@pytest.mark.parametrize('error', [httpx.ReadTimeout('secret'), TimeoutError('secret'),
                                    httpx.ConnectError('secret'), RuntimeError('secret')])
async def test_transport_errors(sdk, proyecto, error):
    sdk.generate.side_effect = error
    expected = IATimeoutError if isinstance(error, (httpx.TimeoutException, TimeoutError)) else IAProviderError
    with pytest.raises(expected):
        await GeminiAdapter('test', 'gemini-2.5-flash').generar_dictamen(proyecto)


async def test_graph_failure(sdk, proyecto):
    adapter = GeminiAdapter('test', 'gemini-2.5-flash')
    adapter.graph = SimpleNamespace(ainvoke=AsyncMock(side_effect=RuntimeError('secret')))
    with pytest.raises(IAGraphError):
        await adapter.generar_dictamen(proyecto)
    sdk.generate.assert_not_called()


async def test_total_timeout(sdk, proyecto):
    async def delayed(**kwargs):
        await asyncio.sleep(1)
    sdk.generate.side_effect = delayed
    with pytest.raises(IATimeoutError):
        await GeminiAdapter('test', 'gemini-2.5-flash', 0.03).generar_dictamen(proyecto)
    sdk.context.__aexit__.assert_awaited_once()
