"""
Flask Admin Dashboard — Quiz Bot
=================================
O'rnatish:
    pip install flask

Ishga tushirish:
    python3 dashboard.py

Alwaysdata da:
    - Sites bo'limida yangi site yarating
    - Type: Flask
    - Application path: dashboard.py
"""

import sqlite3
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

app = Flask(__name__)
app.secret_key = "quiz_dashboard_secret_2024"

# ── Config ──────────────────────────────────────────────────
DB_PATH       = "quiz.db"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


# ── DB helper ───────────────────────────────────────────────
def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


# ── Login required decorator ────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ── Stats helper ─────────────────────────────────────────────
def get_stats():
    with db() as c:
        # Umumiy sonlar
        total_quizzes = c.execute("SELECT COUNT(*) FROM quizzes").fetchone()[0]
        total_scores  = c.execute("SELECT COUNT(*) FROM scores").fetchone()[0]
        total_users   = c.execute("SELECT COUNT(DISTINCT solver_id) FROM scores").fetchone()[0]
        total_creators = c.execute("SELECT COUNT(DISTINCT creator_id) FROM quizzes").fetchone()[0]

        # O'rtacha natija
        avg_row = c.execute(
            "SELECT AVG(CAST(score AS FLOAT) / total * 100) FROM scores"
        ).fetchone()[0]
        avg_score = round(avg_row, 1) if avg_row else 0

        # Aktiv quizlar (muddati o'tmagan)
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        active_quizzes = c.execute(
            "SELECT COUNT(*) FROM quizzes WHERE expires_at > ?", (now,)
        ).fetchone()[0]

        # So'nggi 7 kunlik faollik (o'yinlar soni)
        daily_activity = []
        for i in range(6, -1, -1):
            day = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
            count = c.execute(
                "SELECT COUNT(*) FROM scores WHERE DATE(played_at) = ?", (day,)
            ).fetchone()[0]
            daily_activity.append({"date": day, "count": count})

        # So'nggi 7 kunlik quiz yaratish
        daily_created = []
        for i in range(6, -1, -1):
            day = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
            count = c.execute(
                "SELECT COUNT(*) FROM quizzes WHERE DATE(created_at) = ?", (day,)
            ).fetchone()[0]
            daily_created.append({"date": day, "count": count})

        # Top 10 o'yinchilar
        top_players = c.execute("""
            SELECT solver_name,
                   COUNT(*) as games,
                   AVG(CAST(score AS FLOAT) / total * 100) as avg_pct,
                   MAX(CAST(score AS FLOAT) / total * 100) as best_pct
            FROM scores
            GROUP BY solver_id
            ORDER BY avg_pct DESC
            LIMIT 10
        """).fetchall()

        # So'nggi quizlar
        recent_quizzes = c.execute("""
            SELECT q.quiz_id, q.creator_name, q.created_at, q.expires_at,
                   COUNT(s.id) as plays
            FROM quizzes q
            LEFT JOIN scores s ON q.quiz_id = s.quiz_id
            GROUP BY q.quiz_id
            ORDER BY q.created_at DESC
            LIMIT 10
        """).fetchall()

        # So'nggi o'yinlar
        recent_games = c.execute("""
            SELECT s.solver_name, s.score, s.total,
                   CAST(s.score AS FLOAT) / s.total * 100 as pct,
                   s.played_at, q.creator_name
            FROM scores s
            JOIN quizzes q ON s.quiz_id = q.quiz_id
            ORDER BY s.played_at DESC
            LIMIT 15
        """).fetchall()

        return {
            "total_quizzes":   total_quizzes,
            "total_scores":    total_scores,
            "total_users":     total_users,
            "total_creators":  total_creators,
            "avg_score":       avg_score,
            "active_quizzes":  active_quizzes,
            "daily_activity":  daily_activity,
            "daily_created":   daily_created,
            "top_players":     [dict(r) for r in top_players],
            "recent_quizzes":  [dict(r) for r in recent_quizzes],
            "recent_games":    [dict(r) for r in recent_games],
        }


# ── Routes ───────────────────────────────────────────────────
@app.route("/", methods=["GET"])
@login_required
def index():
    stats = get_stats()
    return render_template("dashboard.html", stats=stats)


@app.route("/api/stats")
@login_required
def api_stats():
    """Avtomatik yangilanish uchun JSON API."""
    return jsonify(get_stats())


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        error = "Username yoki parol noto'g'ri!"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
