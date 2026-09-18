"""Ejercita el SDK real con transporte HTTP simulado, sin acceso a Google."""
import json
import httpx
from google import genai
from app.infrastructure.output.ai.gemini_adapter import GeminiAdapter


async def test_sdk_serializes_schema_and_parses_response(monkeypatch, proyecto, dictamen):
    real_client = genai.Client
    requests = []
    def handler(request):
        requests.append(request)
        body = json.loads(request.content)
        assert body['generationConfig']['responseMimeType'] == 'application/json'
        schema = body['generationConfig']['responseJsonSchema']
        assert schema['properties']['puntaje']['maximum'] == 100
        assert set(schema['required']) == set(dictamen)
        return httpx.Response(200, json={'candidates': [{'content': {
            'role': 'model', 'parts': [{'text': json.dumps(dictamen)}]},
            'finishReason': 'STOP'}]})
    def factory(**kwargs):
        options = kwargs['http_options']
        options.client_args = {'transport': httpx.MockTransport(handler), 'trust_env': False}
        options.async_client_args = {'transport': httpx.MockTransport(handler), 'trust_env': False}
        return real_client(**kwargs)
    monkeypatch.setattr('app.infrastructure.output.ai.gemini_adapter.genai.Client', factory)
    result = await GeminiAdapter('test-key', 'gemini-2.5-flash').generar_dictamen(proyecto)
    assert result.model_dump() == dictamen
    assert len(requests) == 1
    assert requests[0].url.path.endswith('/models/gemini-2.5-flash:generateContent')
