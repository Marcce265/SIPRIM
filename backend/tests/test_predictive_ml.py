from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
import pytest

from backend.main import create_app
from backend.domain.exceptions.pmv1_exceptions import ServicioNoDisponibleError, RecursoPMV1NoEncontradoError
from backend.infrastructure.config.dependencies import get_current_user, get_platform_service
from backend.infrastructure.input.controllers import predictive_ml_controller as controller
from backend.infrastructure.output.ml_mef import predictor


def test_export_matches_sklearn_on_real_reserved_records():
    rows = json.loads((Path(predictor.__file__).parent / 'parity.json').read_text())
    for row in rows:
        result = predictor.predict(row['budget_pen'], row['categories'])
        assert result['cost_probability'] == pytest.approx(row['cost_probability'], abs=1e-12)
        assert result['estimated_duration_days'] == pytest.approx(row['duration_days'], abs=1e-8)
    assert predictor.load_model()['metadata']['synthetic_data'] is False


def test_missing_model_abstains(tmp_path, monkeypatch):
    predictor.load_model.cache_clear()
    monkeypatch.setattr(predictor, 'DIRECTORY', tmp_path)
    with pytest.raises(ServicioNoDisponibleError):
        predictor.load_model()
    predictor.load_model.cache_clear()


@pytest.fixture
def api(monkeypatch):
    app = create_app()
    project_id, version_id, actor = uuid4(), uuid4(), uuid4()
    platform = MagicMock()
    platform.get_project.return_value = {'project_id': project_id, 'project_version_id': version_id,
                                         'code': 'EXP-TEST', 'estimated_budget_pen': 250000}
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.transaction.return_value.__enter__.return_value = connection
    connection.execute.return_value.fetchone.return_value = (version_id,)
    monkeypatch.setattr(controller.psycopg, 'connect', lambda *args, **kwargs: connection)
    app.dependency_overrides[get_current_user] = lambda: {'sub': str(actor), 'roles': ['PLANNER']}
    app.dependency_overrides[get_platform_service] = lambda: platform
    categories = predictor.load_model()['metadata']['categories']
    payload = {'project_version_id': str(version_id), 'function': 'TRANSPORTE', 'department': 'JUNIN',
               'execution_mode': 'ADMINISTRACIÓN DIRECTA', 'investment_type': 'PROYECTO DE INVERSION', 'planned_days': 180}
    assert payload['execution_mode'] in categories['DES_MODALIDAD']
    with TestClient(app) as client:
        yield client, app, platform, connection, project_id, version_id, actor, payload


def test_prediction_uses_registered_budget_and_is_persisted(api):
    client, _, platform, conn, project, version, actor, payload = api
    response = client.post(f'/api/v1/ml/projects/{project}/predict', json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['budget_pen'] == 250000
    assert body['project_version_id'] == str(version)
    assert body['difference_days'] == pytest.approx(body['estimated_duration_days'] - 180)
    inserts = [call for call in conn.execute.call_args_list if 'INSERT INTO audit_events' in call.args[0]]
    assert len(inserts) == 1
    assert inserts[0].args[1][0] == actor
    assert inserts[0].args[1][2].obj['prediction_id'] == body['prediction_id']
    with pytest.raises(KeyError):
        body['demo']


@pytest.mark.parametrize('changes', [{'budget_pen': 1}, {'function': 'INVENTADO'}, {'planned_days': 0}, {'planned_days': 2.5}])
def test_invalid_or_invented_inputs_are_rejected(api, changes):
    client, _, _, conn, project, _, _, payload = api
    response = client.post(f'/api/v1/ml/projects/{project}/predict', json={**payload, **changes})
    assert response.status_code == 422
    assert not any('INSERT INTO' in call.args[0] for call in conn.execute.call_args_list)


def test_stale_version_is_rejected(api):
    client, _, _, conn, project, _, _, payload = api
    response = client.post(f'/api/v1/ml/projects/{project}/predict', json={**payload, 'project_version_id': str(uuid4())})
    assert response.status_code == 409
    conn.execute.assert_not_called()


def test_missing_project_is_not_replaced_with_demo(api):
    client, _, platform, conn, project, _, _, payload = api
    platform.get_project.side_effect = RecursoPMV1NoEncontradoError('Proyecto no encontrado')
    assert client.post(f'/api/v1/ml/projects/{project}/predict', json=payload).status_code == 404
    conn.execute.assert_not_called()


def test_legal_role_can_read_but_cannot_predict(api):
    client, app, _, conn, project, _, actor, payload = api
    app.dependency_overrides[get_current_user] = lambda: {'sub': str(actor), 'roles': ['LEGAL_ADVISOR']}
    assert client.get('/api/v1/ml/model').status_code == 200
    assert client.post(f'/api/v1/ml/projects/{project}/predict', json=payload).status_code == 403
    conn.execute.assert_not_called()


def test_latest_is_read_for_current_project_version(api):
    client, _, _, conn, project, version, _, _ = api
    conn.execute.return_value.fetchone.return_value = ({'prediction_id': 'saved-id'},)
    assert client.get(f'/api/v1/ml/projects/{project}/latest').json() == {'prediction_id': 'saved-id'}
    assert conn.execute.call_args.args[1] == (project, str(version))


def test_authentication_is_required():
    with TestClient(create_app()) as client:
        assert client.get('/api/v1/ml/model').status_code == 401
