"""
Benchmark Repo 1: flask_to_fastapi
────────────────────────────────────
A legacy Flask + raw sqlite3 CRUD app for a product catalogue.
The agent's task: migrate to FastAPI + SQLAlchemy, keep all tests green.
"""
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
DATABASE = "products.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


@app.route("/products", methods=["GET"])
def list_products():
    conn = get_db()
    rows = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify(dict(row))


@app.route("/products", methods=["POST"])
def create_product():
    data = request.get_json()
    name = data.get("name")
    price = data.get("price")
    stock = data.get("stock", 0)
    if not name or price is None:
        return jsonify({"error": "name and price required"}), 400
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO products (name, price, stock) VALUES (?, ?, ?)",
        (name, price, stock)
    )
    conn.commit()
    product_id = cur.lastrowid
    conn.close()
    return jsonify({"id": product_id, "name": name, "price": price, "stock": stock}), 201


@app.route("/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return jsonify({"deleted": product_id})


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
