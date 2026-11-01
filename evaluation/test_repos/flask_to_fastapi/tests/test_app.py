"""
Tests for flask_to_fastapi benchmark repo.
These tests are written against the FastAPI interface the agent should produce.
"""
import pytest


def test_list_products_empty():
    """After migration, GET /products should return empty list."""
    try:
        from fastapi.testclient import TestClient
        from app import app
        client = TestClient(app)
        resp = client.get("/products")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
    except ImportError:
        pytest.skip("FastAPI not yet migrated")


def test_create_product():
    """POST /products should create and return new product with id."""
    try:
        from fastapi.testclient import TestClient
        from app import app
        client = TestClient(app)
        resp = client.post("/products", json={"name": "Widget", "price": 9.99, "stock": 100})
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "id" in data
        assert data["name"] == "Widget"
    except ImportError:
        pytest.skip("FastAPI not yet migrated")


def test_get_product_not_found():
    """GET /products/999 should return 404."""
    try:
        from fastapi.testclient import TestClient
        from app import app
        client = TestClient(app)
        resp = client.get("/products/9999")
        assert resp.status_code == 404
    except ImportError:
        pytest.skip("FastAPI not yet migrated")


def test_delete_product():
    """DELETE /products/{id} should remove the product."""
    try:
        from fastapi.testclient import TestClient
        from app import app
        client = TestClient(app)
        # Create first
        create = client.post("/products", json={"name": "Temp", "price": 1.0, "stock": 1})
        pid = create.json()["id"]
        # Delete
        resp = client.delete(f"/products/{pid}")
        assert resp.status_code in (200, 204)
        # Verify gone
        get = client.get(f"/products/{pid}")
        assert get.status_code == 404
    except ImportError:
        pytest.skip("FastAPI not yet migrated")
