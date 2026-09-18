import ast
from pathlib import Path
from unittest.mock import AsyncMock
import pytest
from app.ai.graph.evaluation_graph import build_evaluation_graph
from app.application.services.ai_evaluation_service import AIEvaluationService
from app.application.use_cases.evaluar_proyecto import EvaluarProyecto
from app.domain.ports.ia_service import IIAService
from app.domain.errors import IAInvalidResponseError, IARateLimitError
from app.domain.value_objects.dictamen_ia import DictamenIA
from app.infrastructure.config.settings import Settings


async def test_use_case_uses_port(proyecto, dictamen):
    port = AsyncMock(spec=IIAService)
    port.generar_dictamen.return_value = DictamenIA(**dictamen)
    result = await EvaluarProyecto(AIEvaluationService(port)).ejecutar(proyecto)
    assert result.model_dump() == dictamen
    port.generar_dictamen.assert_awaited_once_with(proyecto)


async def test_use_case_rejects_invalid(proyecto):
    port = AsyncMock(spec=IIAService)
    port.generar_dictamen.return_value = {'puntaje': 200}
    with pytest.raises(IAInvalidResponseError):
        await EvaluarProyecto(port).ejecutar(proyecto)


async def test_use_case_preserves_error(proyecto):
    port = AsyncMock(spec=IIAService)
    port.generar_dictamen.side_effect = IARateLimitError()
    with pytest.raises(IARateLimitError):
        await EvaluarProyecto(port).ejecutar(proyecto)


async def test_real_graph_order(proyecto, dictamen):
    generate = AsyncMock(return_value=DictamenIA(**dictamen))
    graph = build_evaluation_graph(generate)
    updates = [u async for u in graph.astream({'proyecto': proyecto}, stream_mode='updates')]
    assert [next(iter(u)) for u in updates] == ['coordinador', 'tecnico', 'dictamen']
    assert updates[-1]['dictamen']['dictamen'].puntaje == 65
    assert '500.00' in generate.call_args.args[0]['analisis_tecnico']


def test_settings_env_and_secret(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'private-test-value')
    monkeypatch.setenv('AI_MODEL', 'test-model')
    monkeypatch.setenv('APP_ENV', 'test')
    settings = Settings(_env_file=None)
    assert settings.gemini_api_key.get_secret_value() == 'private-test-value'
    assert settings.ai_model == 'test-model'
    assert settings.app_env == 'test'
    assert 'private-test-value' not in repr(settings)


def test_domain_and_application_boundaries():
    for directory in ['app/domain', 'app/application']:
        for path in Path(directory).rglob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Import):
                    imports = [n.name for n in node.names]
                elif isinstance(node, ast.ImportFrom):
                    imports = [node.module or '']
                else:
                    continue
                for name in imports:
                    assert not name.startswith(('fastapi', 'google', 'langgraph', 'qdrant', 'sqlalchemy',
                                                'app.infrastructure', 'app.ai')), (path, name)
                    if directory == 'app/domain':
                        assert not name.startswith('app.application'), (path, name)
