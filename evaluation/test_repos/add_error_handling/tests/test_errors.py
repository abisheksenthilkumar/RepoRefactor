"""
Tests for add_error_handling benchmark repo.
Verifies proper HTTP status codes, error responses, and no print() calls.
"""
import ast
import os
import json
import pytest


@pytest.fixture
def client():
    from app import app, init_db
    app.config["TESTING"] = True
    with app.test_client() as c:
        with app.app_context():
            init_db()
        yield c


def test_get_nonexistent_order_returns_404(client):
    """GET /orders/9999 should return 404, not crash."""
    resp = client.get("/orders/9999")
    assert resp.status_code == 404, f"Expected 404 for missing order, got {resp.status_code}"


def test_create_order_missing_field_returns_400(client):
    """POST with missing fields should return 400, not 500."""
    resp = client.post(
        "/orders",
        data=json.dumps({"customer": "Alice"}),   # missing item, qty, price
        content_type="application/json",
    )
    assert resp.status_code == 400, f"Expected 400 for bad input, got {resp.status_code}"


def test_create_order_invalid_qty_returns_400(client):
    """POST with non-numeric qty should return 400, not 500."""
    resp = client.post(
        "/orders",
        data=json.dumps({"customer": "Bob", "item": "Widget", "qty": "abc", "price": 10.0}),
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_create_and_get_order(client):
    """Happy path: create then retrieve an order."""
    create_resp = client.post(
        "/orders",
        data=json.dumps({"customer": "Charlie", "item": "Gadget", "qty": 2, "price": 15.0}),
        content_type="application/json",
    )
    assert create_resp.status_code == 201
    order_id = create_resp.get_json()["id"]
    get_resp = client.get(f"/orders/{order_id}")
    assert get_resp.status_code == 200
    assert get_resp.get_json()["customer"] == "Charlie"


def test_total_revenue_returns_zero_on_empty(client):
    """GET /orders/total on empty DB should return 0, not crash."""
    resp = client.get("/orders/total")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["revenue"] is not None


def test_no_print_statements_in_app():
    """app.py must not use print() — only logging module."""
    base = os.path.dirname(os.path.dirname(__file__))
    app_file = os.path.join(base, "app.py")
    with open(app_file, encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source)
    print_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "print"
    ]
    assert not print_calls, f"Found {len(print_calls)} print() calls — replace with logging"
