"""
Benchmark Repo 2: sql_injection_fix
──────────────────────────────────────
A Flask app with 3 blatant SQL injection vulnerabilities.
Agent task: write regression tests first, then fix with parameterised queries.
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
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT
            )
        """)
        _conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                content TEXT
            )
        """)
        _conn.commit()
    return _conn


def init_db():
    db = get_db()
    db.execute("INSERT OR IGNORE INTO users (username, password, email) VALUES ('admin', 'secret', 'admin@example.com')")
    db.commit()


@app.route("/login", methods=["POST"])
def login():
    """VULNERABLE: SQL injection in login query."""
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    db = get_db()
    # BUG: direct string interpolation — injectable
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    row = db.execute(query).fetchone()
    if row:
        return jsonify({"status": "ok", "user": dict(row)})
    return jsonify({"status": "unauthorized"}), 401


@app.route("/users/<username>", methods=["GET"])
def get_user(username):
    """VULNERABLE: SQL injection in user lookup."""
    db = get_db()
    # BUG: direct string interpolation
    query = f"SELECT id, username, email FROM users WHERE username = '{username}'"
    row = db.execute(query).fetchone()
    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row))


@app.route("/notes/search", methods=["GET"])
def search_notes():
    """VULNERABLE: SQL injection in search."""
    term = request.args.get("q", "")
    db = get_db()
    # BUG: direct string interpolation
    query = f"SELECT * FROM notes WHERE content LIKE '%{term}%'"
    rows = db.execute(query).fetchall()
    return jsonify([dict(r) for r in rows])


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
