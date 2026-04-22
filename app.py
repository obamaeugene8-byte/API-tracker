from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)
app.secret_key = "Bestreader"

PLAN_PRICE = 5000
TRIAL_DAYS = 3   # ✅ CHANGED TO 3 DAYS

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT,
        api_key TEXT UNIQUE,
        is_active INTEGER DEFAULT 0,
        expires_at TEXT,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        api_key TEXT,
        endpoint TEXT,
        timestamp TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("login.html")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["POST"])
def register():
    data = request.json

    email = data["email"]
    password = data["password"]

    api_key = str(uuid.uuid4())
    created_at = datetime.now()
    expires_at = created_at + timedelta(days=TRIAL_DAYS)

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    INSERT INTO users (email, password, api_key, is_active, expires_at, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (email, password, api_key, 0, expires_at, created_at))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Account created (3-day trial active)",
        "api_key": api_key,
        "price": PLAN_PRICE
    })

# ---------------- LOGIN ----------------
@app.route("/login", methods=["POST"])
def login():
    data = request.json

    email = data["email"]
    password = data["password"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    SELECT api_key FROM users
    WHERE email=? AND password=?
    """, (email, password))

    user = c.fetchone()
    conn.close()

    if user:
        return jsonify({"api_key": user[0]})

    return jsonify({"error": "Invalid login"}), 401

# ---------------- LOG USAGE ----------------
@app.route("/log", methods=["POST"])
def log():
    data = request.json

    api_key = data.get("api_key")
    endpoint = data.get("endpoint")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT is_active FROM users WHERE api_key=?", (api_key,))
    user = c.fetchone()

    if not user:
        return {"error": "Invalid API key"}, 401

    if user[0] == 0:
        return {"error": "Inactive account. Pay KES 5000/month"}, 403

    c.execute("""
    INSERT INTO logs (api_key, endpoint, timestamp)
    VALUES (?, ?, ?)
    """, (api_key, endpoint, datetime.now()))

    conn.commit()
    conn.close()

    return {"message": "Logged"}

# ---------------- ACTIVATE USER (MANUAL PAYMENT) ----------------
@app.route("/activate", methods=["POST"])
def activate():
    data = request.json
    api_key = data["api_key"]

    new_expiry = datetime.now() + timedelta(days=30)

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    UPDATE users
    SET is_active=1, expires_at=?
    WHERE api_key=?
    """, (new_expiry, api_key))

    conn.commit()
    conn.close()

    return {"message": "User activated for 30 days"}

# ---------------- DASHBOARD ----------------
@app.route("/dashboard/<api_key>")
def dashboard(api_key):

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    SELECT endpoint, COUNT(*)
    FROM logs
    WHERE api_key=?
    GROUP BY endpoint
    """, (api_key,))

    data = c.fetchall()

    c.execute("SELECT is_active FROM users WHERE api_key=?", (api_key,))
    user = c.fetchone()

    status = user and user[0] == 1

    conn.close()

    return render_template("dashboard.html", data=data, status=status)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
