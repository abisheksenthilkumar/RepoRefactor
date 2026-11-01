"""
demo_repo/app.py
─────────────────
A deliberately BAD legacy Flask + SQLite application.
This is the "before" state — the agent transforms this into a clean,
modern, secure FastAPI application (the "after" state for the demo).

Intentional issues:
  - Flask (not FastAPI)
  - Synchronous SQLite (not async SQLAlchemy)
  - SQL Injection vulnerability (CWE-89)
  - Hardcoded secret key (CWE-798)
  - debug=True in production (CWE-16)
  - No error handling
  - No input validation
  - No logging
  - Python 2-style print statements in places
  - No type hints
  - Mixed indentation
"""

from flask import Flask, request, jsonify
import sqlite3
import hashlib

app = Flask(__name__)
app.secret_key = "super_secret_key_123"  # SECURITY ISSUE: hardcoded secret

DATABASE = "users.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            email TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


@app.route("/users", methods=["GET"])
def get_users():
    username = request.args.get("username", "")
    conn = get_db()
    # SECURITY ISSUE: SQL Injection vulnerability
    query = f"SELECT id, username, email FROM users WHERE username = '{username}'"
    cursor = conn.execute(query)
    users = cursor.fetchall()
    conn.close()
    return jsonify(users)


@app.route("/users", methods=["POST"])
def create_user():
    data = request.json
    username = data["username"]
    password = data["password"]
    email = data.get("email", "")

    # SECURITY ISSUE: MD5 is cryptographically weak for passwords
    hashed_password = hashlib.md5(password.encode()).hexdigest()

    conn = get_db()
    conn.execute(
        "INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
        (username, hashed_password, email)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "User created"}), 201


@app.route("/products", methods=["GET"])
def get_products():
    conn = get_db()
    cursor = conn.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()
    return jsonify(products)


@app.route("/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    conn = get_db()
    cursor = conn.execute(
        f"SELECT * FROM products WHERE id = {product_id}"  # SECURITY ISSUE: SQL Injection
    )
    product = cursor.fetchone()
    conn.close()
    if not product:
        return jsonify({"error": "not found"}), 404
    return jsonify(product)


@app.route("/products", methods=["POST"])
def create_product():
    data = request.json
    name = data["name"]
    price = data["price"]
    stock = data.get("stock", 0)
    conn = get_db()
    conn.execute(
        "INSERT INTO products (name, price, stock) VALUES (?, ?, ?)",
        (name, price, stock)
    )
    conn.commit()
    conn.close()
    print("Product created:", name)  # Python 2-style debug output
    return jsonify({"message": "Product created"}), 201


@app.route("/search", methods=["GET"])
def search_products():
    q = request.args.get("q", "")
    conn = get_db()
    # SECURITY ISSUE: SQL Injection
    cursor = conn.execute(
        f"SELECT * FROM products WHERE name LIKE '%{q}%'"
    )
    results = cursor.fetchall()
    conn.close()
    return jsonify(results)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)  # SECURITY ISSUE: debug=True
