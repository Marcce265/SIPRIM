import pytest
from api.index import configure_preview_databases

KEYS = ('DATABASE_URL', 'AUTH_DB_URL', 'PLATFORM_DB_URL', 'ECONOMIC_DB_URL')


def test_production_ignores_preview_host(monkeypatch):
    monkeypatch.setenv('VERCEL_ENV', 'production')
    monkeypatch.setenv('SIPRIM_PREVIEW_DB_HOST', 'test.neon.tech')
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:private@production.neon.tech/db')
    configure_preview_databases()
    assert 'production.neon.tech' in __import__('os').environ['DATABASE_URL']


def test_preview_preserves_credentials_database_and_options(monkeypatch):
    import os
    monkeypatch.setenv('VERCEL_ENV', 'preview')
    monkeypatch.setenv('SIPRIM_PREVIEW_DB_HOST', 'ep-test.neon.tech')
    for key in KEYS:
        monkeypatch.setenv(key, 'postgresql+psycopg://user:p%40ss@production.neon.tech/db?sslmode=require')
    configure_preview_databases()
    for key in KEYS:
        assert os.environ[key] == 'postgresql+psycopg://user:p%40ss@ep-test.neon.tech/db?sslmode=require'


def test_preview_rejects_external_credential_destination(monkeypatch):
    monkeypatch.setenv('VERCEL_ENV', 'preview')
    monkeypatch.setenv('SIPRIM_PREVIEW_DB_HOST', 'attacker.example')
    with pytest.raises(ValueError):
        configure_preview_databases()
