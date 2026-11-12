"""ASGI entry point and optional database isolation for Vercel previews."""
import os
from urllib.parse import urlsplit, urlunsplit


def configure_preview_databases() -> None:
    """Reuse private credentials while directing only previews to a Neon branch."""
    host = os.environ.get("SIPRIM_PREVIEW_DB_HOST")
    if not host or os.environ.get("VERCEL_ENV") != "preview":
        return
    if not host.endswith(".neon.tech") or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789.-" for c in host):
        raise ValueError("SIPRIM_PREVIEW_DB_HOST must be a Neon endpoint hostname")
    for key in ("DATABASE_URL", "AUTH_DB_URL", "PLATFORM_DB_URL", "ECONOMIC_DB_URL"):
        value = os.environ.get(key)
        if not value:
            raise ValueError(f"Missing private database configuration: {key}")
        parts = urlsplit(value)
        credentials, separator, _ = parts.netloc.rpartition("@")
        if not separator:
            raise ValueError(f"Invalid database configuration: {key}")
        # The branch inherits the roles and passwords; no new credential is created.
        os.environ[key] = urlunsplit((parts.scheme, credentials + "@" + host, parts.path, parts.query, parts.fragment))


configure_preview_databases()
from backend.main import app  # noqa: E402
