"""Auth flow against the live DB: signup -> login -> me; wrong creds rejected.
Skips when TimescaleDB isn't reachable (same guard as test_storage_db)."""
import uuid

import psycopg2
import pytest

from api.config import settings


def _db_available() -> bool:
    try:
        psycopg2.connect(settings.pg_dsn, connect_timeout=2).close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_available(), reason="TimescaleDB not reachable (run: docker compose up -d timescaledb)"
)


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from api.main import app

    return TestClient(app)


@pytest.fixture()
def email():
    return f"test-{uuid.uuid4().hex[:10]}@example.com"


def test_signup_login_me_roundtrip(client, email):
    r = client.post("/api/auth/signup", json={"email": email, "password": "hunter22"})
    assert r.status_code == 201
    token = r.json()["token"]
    assert r.json()["user"]["email"] == email

    r2 = client.post("/api/auth/login", json={"email": email, "password": "hunter22"})
    assert r2.status_code == 200

    r3 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r3.status_code == 200
    assert r3.json()["user"]["email"] == email


def test_duplicate_email_409(client, email):
    assert client.post("/api/auth/signup", json={"email": email, "password": "hunter22"}).status_code == 201
    assert client.post("/api/auth/signup", json={"email": email, "password": "other123"}).status_code == 409


def test_wrong_password_401(client, email):
    client.post("/api/auth/signup", json={"email": email, "password": "hunter22"})
    r = client.post("/api/auth/login", json={"email": email, "password": "wrong-pass"})
    assert r.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
