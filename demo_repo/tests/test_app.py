"""
demo_repo/tests/test_app.py
────────────────────────────
Basic tests for the legacy Flask app.
These tests will FAIL or pass in unexpected ways before refactoring
and should all PASS cleanly after the agent runs.
"""

import pytest
from demo_repo.app import app, init_db
import json


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["DATABASE"] = ":memory:"
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client


def test_get_products_empty(client):
    resp = client.get("/products")
    assert resp.status_code == 200
    assert resp.json == []


def test_create_and_get_product(client):
    resp = client.post(
        "/products",
        data=json.dumps({"name": "Widget", "price": 9.99, "stock": 50}),
        content_type="application/json",
    )
    assert resp.status_code == 201

    resp = client.get("/products")
    assert resp.status_code == 200
    data = resp.json
    assert len(data) == 1
    assert data[0][1] == "Widget"


def test_create_user(client):
    resp = client.post(
        "/users",
        data=json.dumps({"username": "alice", "password": "pass123", "email": "alice@example.com"}),
        content_type="application/json",
    )
    assert resp.status_code == 201


def test_search_products(client):
    client.post(
        "/products",
        data=json.dumps({"name": "Widget Pro", "price": 19.99}),
        content_type="application/json",
    )
    resp = client.get("/products?search=Widget")
    assert resp.status_code == 200
