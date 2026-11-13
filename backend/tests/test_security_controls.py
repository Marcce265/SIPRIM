from datetime import datetime, timedelta, timezone
from uuid import uuid4
import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from backend.application.services.validated_auth_service import ValidatedAuthService as AuthService
from backend.domain.exceptions.pmv1_exceptions import CredencialesInvalidasError
from backend.infrastructure.config.dependencies import get_current_user
from backend.infrastructure.config.settings import Settings
from backend.main import create_app


@pytest.mark.parametrize('method,path', [
    ('get', '/api/v1/proyectos/1'),
    ('post', '/api/v1/proyectos'),
    ('post', '/api/v1/proyectos/1/validar'),
    ('post', '/api/v1/proyectos/1/evaluacion-economica'),
    ('post', '/api/v1/proyectos/1/evaluacion-juridica'),
    ('post', '/api/v1/proyectos/1/evaluacion-ia'),
])
def test_legacy_requires_authentication(method, path):
    with TestClient(create_app()) as client:
        response = getattr(client, method)(path)
    assert response.status_code == 401
    assert response.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('roles', [['CITIZEN'], ['LEGAL_ADVISOR']])
def test_legacy_write_rejects_other_roles(roles):
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {'sub': str(uuid4()), 'roles': roles}
    with TestClient(app) as client:
        assert client.post('/api/v1/proyectos', json={'nombre': 'Proyecto de prueba'}).status_code == 403
        assert client.post('/api/v1/proyectos/1/evaluacion-ia').status_code == 403


def test_unexpected_error_is_sanitized_and_correlated(caplog):
    app = create_app()
    @app.get('/api/test-private-failure')
    def fail():
        raise RuntimeError('PRIVATE_SENTINEL')
    with TestClient(app) as client:
        response = client.get('/api/test-private-failure?secret=PRIVATE_SENTINEL')
    assert response.status_code == 500
    assert response.json()['request_id'] == response.headers['x-request-id']
    assert 'PRIVATE_SENTINEL' not in response.text
    assert 'PRIVATE_SENTINEL' not in caplog.text
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert response.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('missing', ['exp', 'iat', 'sub', 'roles', 'iss', 'aud'])
def test_jwt_requires_claims(missing):
    auth = AuthService('unused', 'x'*48, 'issuer', 'audience', 60)
    now = datetime.now(timezone.utc)
    claims = {'exp': now+timedelta(hours=1), 'iat': now, 'sub': str(uuid4()),
              'roles': ['PLANNER'], 'iss': 'issuer', 'aud': 'audience'}
    del claims[missing]
    with pytest.raises(CredencialesInvalidasError):
        auth.decode(jwt.encode(claims, 'x'*48, algorithm='HS256'))


def test_normal_jwt_remains_compatible():
    auth = AuthService('unused', 'x'*48, 'issuer', 'audience', 60)
    user_id = uuid4()
    assert auth.decode(auth.issue_token(user_id, ['PLANNER'])['access_token'])['sub'] == str(user_id)


@pytest.mark.parametrize('roles', ['PLANNER', [1], {'ADMIN': True}])
def test_jwt_rejects_invalid_role_types(roles):
    auth = AuthService('unused', 'x'*48, 'issuer', 'audience', 60)
    claims = auth.decode(auth.issue_token(uuid4(), ['PLANNER'])['access_token'])
    claims['roles'] = roles
    with pytest.raises(CredencialesInvalidasError):
        auth.decode(jwt.encode(claims, 'x'*48, algorithm='HS256'))


def test_production_rejects_default_secret(monkeypatch):
    monkeypatch.delenv('JWT_SECRET', raising=False)
    monkeypatch.delenv('VERCEL', raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env='production')
    assert Settings(_env_file=None, app_env='production', jwt_secret='x'*48)
    monkeypatch.setenv('VERCEL', '1')
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
