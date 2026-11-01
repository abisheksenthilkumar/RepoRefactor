"""
Tests for sql_injection_fix benchmark repo.
These tests verify SQL injection is NOT possible after the fix.
"""
import pytest
import json


@pytest.fixture
def client():
    from app import app, init_db
    app.config["TESTING"] = True
    with app.test_client() as c:
        with app.app_context():
            init_db()
        yield c


def test_login_sql_injection_blocked(client):
    """Classic ' OR '1'='1 should NOT bypass login."""
    resp = client.post(
        "/login",
        data=json.dumps({"username": "' OR '1'='1", "password": "' OR '1'='1"}),
        content_type="application/json",
    )
    assert resp.status_code == 401, "SQL injection bypassed login!"


def test_login_valid_credentials(client):
    """Valid credentials should still work after the fix."""
    resp = client.post(
        "/login",
        data=json.dumps({"username": "admin", "password": "secret"}),
        content_type="application/json",
    )
    assert resp.status_code == 200


def test_user_lookup_injection_blocked(client):
    """Injection in user lookup should not return all rows."""
    resp = client.get("/users/' OR '1'='1")
    # Should be 404 not found, not a dump of all users
    assert resp.status_code in (404, 400)


def test_search_sql_injection_blocked(client):
    """Search with injection payload should not cause DB errors."""
    resp = client.get("/notes/search?q='; DROP TABLE users; --")
    assert resp.status_code == 200
    # DB should still be intact
    check = client.get("/users/admin")
    assert check.status_code == 200
