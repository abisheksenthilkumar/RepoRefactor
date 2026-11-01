"""
Benchmark Repo 3: hardcoded_secrets
──────────────────────────────────────
A data pipeline script with hardcoded credentials everywhere.
Agent task: move all secrets to .env / os.getenv(), add .env.example.
"""
import sqlite3
import hashlib
import requests   # noqa: F401 — available in real runs

# ── HARDCODED SECRETS (all must be moved to env vars) ─────────────────────────
DATABASE_URL    = "postgresql://admin:SuperSecret123!@prod-db.internal:5432/appdb"
AWS_ACCESS_KEY  = "AKIAIOSFODNN7EXAMPLEFAKE"
AWS_SECRET_KEY  = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
STRIPE_API_KEY  = "sk_live_REPLACE_ME_hardcoded_key_example_only"
SENDGRID_KEY    = "SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
ADMIN_PASSWORD  = "admin123"
SECRET_TOKEN    = "my-super-secret-jwt-token-do-not-share"
DEBUG           = True   # should be False in prod, loaded from env


def get_db_connection():
    """Returns a fake local DB for testing (replaces Postgres connection)."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
    return conn


def send_email(to: str, subject: str, body: str) -> bool:
    """Send email via SendGrid. Key must NOT be hardcoded."""
    # BUG: key hardcoded above
    headers = {"Authorization": f"Bearer {SENDGRID_KEY}"}
    print(f"Would send email to {to} with key {SENDGRID_KEY[:10]}...")
    return True


def charge_customer(amount: float, customer_id: str) -> dict:
    """Charge via Stripe. Key must NOT be hardcoded."""
    # BUG: key hardcoded above
    print(f"Charging {amount} with key {STRIPE_API_KEY[:12]}...")
    return {"status": "charged", "amount": amount}


def hash_password(password: str) -> str:
    """Hash a password (using SHA256 — acceptable for this task)."""
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate(username: str, password: str) -> bool:
    """Check credentials against hardcoded admin password."""
    # BUG: ADMIN_PASSWORD hardcoded
    return username == "admin" and password == ADMIN_PASSWORD


def get_users():
    """Fetch all users from DB."""
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "email": r[2]} for r in rows]


if __name__ == "__main__":
    print("Pipeline started")
    print(f"DB: {DATABASE_URL}")
    print(f"AWS key: {AWS_ACCESS_KEY}")
