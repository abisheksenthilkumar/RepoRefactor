"""
Benchmark Repo 4: add_error_handling
────────────────────────────────────────
A Flask REST API with zero error handling — bare exceptions, no logging,
wrong HTTP status codes, print() statements everywhere.
Agent task: add try/except, replace print() with logging, return proper HTTP codes.
"""
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
DATABASE = ":memory:"
_conn = None


def get_db():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DATABASE, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer TEXT NOT NULL,
                item TEXT NOT NULL,
                qty INTEGER NOT NULL,
                total REAL NOT NULL
            )
        """)
        _conn.commit()
    return _conn


def init_db():
    get_db()


@app.route("/orders", methods=["GET"])
def list_orders():
    print("Listing all orders")          # BUG: should use logging
    db = get_db()
    rows = db.execute("SELECT * FROM orders").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/orders/<int:order_id>", methods=["GET"])
def get_order(order_id):
    print(f"Getting order {order_id}")   # BUG: should use logging
    db = get_db()
    row = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    # BUG: no 404 handling — returns None which crashes jsonify
    return jsonify(dict(row))


@app.route("/orders", methods=["POST"])
def create_order():
    print("Creating order")              # BUG: should use logging
    data = request.get_json()
    # BUG: no input validation — KeyError if fields missing
    customer = data["customer"]
    item = data["item"]
    qty = int(data["qty"])               # BUG: ValueError if not a number
    price = float(data["price"])
    total = qty * price
    db = get_db()
    cur = db.execute(
        "INSERT INTO orders (customer, item, qty, total) VALUES (?, ?, ?, ?)",
        (customer, item, qty, total)
    )
    db.commit()
    print(f"Order created: {cur.lastrowid}")  # BUG: should use logging
    return jsonify({"id": cur.lastrowid, "total": total})


@app.route("/orders/<int:order_id>", methods=["DELETE"])
def delete_order(order_id):
    print(f"Deleting order {order_id}")  # BUG: should use logging
    db = get_db()
    db.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    db.commit()
    return jsonify({"deleted": order_id})


@app.route("/orders/total", methods=["GET"])
def total_revenue():
    print("Calculating total revenue")   # BUG: should use logging
    db = get_db()
    result = db.execute("SELECT SUM(total) as revenue FROM orders").fetchone()
    # BUG: no handling if result is None
    return jsonify({"revenue": result["revenue"]})


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
