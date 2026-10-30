"""Pruebas controladas del adaptador: NO consumen Gemini real."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from google.genai import errors
from pydantic import ValidationError

from backend.application.dto.evaluacion_ia_dto import DictamenIAResponse
from backend.domain.exceptions.ia_exceptions import (
    IAAuthenticationError, IAEmptyResponseError, IAInvalidResponseError,
    IARateLimitError, IATimeoutError, IAProviderError, IAConfigurationError,
)
from backend.infrastructure.output.ai.gemini_adapter import GeminiAdapter

VALID = dict(puntaje=35.0, viabilidad='BAJA', justificacion='Sin sustento tecnico suficiente.',
             observaciones=['Faltan metrados.'], recomendaciones=['Revision profesional.'])


@pytest.mark.parametrize('score,label', [(0.,'BAJA'),(39.99,'BAJA'),(40.,'MEDIA'),(69.99,'MEDIA'),(70.,'ALTA'),(100.,'ALTA')])
def test_limites_de_viabilidad(score, label):
    assert DictamenIAResponse(**{**VALID,'puntaje':score,'viabilidad':label}).viabilidad == label


@pytest.mark.parametrize('changes', [dict(puntaje=90.,viabilidad='BAJA'),dict(observaciones=[' ']),dict(recomendaciones=['']),dict(puntaje=float('nan'))])
def test_rechaza_dictamen_incoherente(changes):
    with pytest.raises(ValidationError):
        DictamenIAResponse(**{**VALID, **changes})


def run_generate(response=None, failure=None):
    class FakeClient:
        def __init__(self, **kwargs):
            self.aio = self
            self.models = self
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def generate_content(self, **kwargs):
            if failure:
                raise failure
            return SimpleNamespace(text=response)
    with patch('backend.infrastructure.output.ai.gemini_adapter.genai.Client', FakeClient):
        return asyncio.run(GeminiAdapter('test-only-key','test-only-model')._generate({}))


@pytest.mark.parametrize('payload,expected', [(None,IAEmptyResponseError),('  ',IAEmptyResponseError),('not json',IAInvalidResponseError),(json.dumps({**VALID,'viabilidad':'ALTA'}),IAInvalidResponseError)])
def test_salida_vacia_invalida(payload, expected):
    with pytest.raises(expected):
        run_generate(payload)


@pytest.mark.parametrize('code,expected', [(401,IAAuthenticationError),(403,IAAuthenticationError),(429,IARateLimitError),(504,IATimeoutError),(503,IAProviderError)])
def test_errores_proveedor(code, expected):
    with pytest.raises(expected) as error:
        run_generate(failure=errors.APIError(code, {'error':{'message':'PRIVATE_SENTINEL'}}))
    assert 'PRIVATE_SENTINEL' not in str(error.value)


def test_timeout_transporte():
    with pytest.raises(IATimeoutError):
        run_generate(failure=httpx.ReadTimeout('PRIVATE_SENTINEL'))


def test_salida_valida():
    assert run_generate(json.dumps(VALID)).puntaje == 35.


def test_sin_clave_no_llama_proveedor():
    with pytest.raises(IAConfigurationError):
        asyncio.run(GeminiAdapter(None,'test-only-model').generar_dictamen({}))


def test_timeout_grafo():
    async def slow_generate(context):
        await asyncio.sleep(1)
    adapter = GeminiAdapter('test-only-key','test-only-model',.01)
    from backend.infrastructure.output.ai.evaluation_graph import build_evaluation_graph
    adapter._graph = build_evaluation_graph(slow_generate)
    with pytest.raises(IATimeoutError):
        asyncio.run(adapter.generar_dictamen(dict(nombre='Prueba',descripcion='Caso controlado',ubicacion='El Tambo',presupuesto=1000,beneficiarios=10,tipo_proyecto='Parque')))
