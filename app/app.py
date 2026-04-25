import json
import os

import psycopg2
import redis
from flask import Flask, redirect, render_template, request, url_for
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/todoapp")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

cache = redis.from_url(REDIS_URL, decode_responses=True)


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY,
                    text TEXT NOT NULL
                )
                """
            )


def fetch_items():
    cached = cache.get("items:list")
    if cached:
        return json.loads(cached)

    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, text FROM items ORDER BY id DESC")
            rows = cur.fetchall()
            items = [{"id": row["id"], "text": row["text"]} for row in rows]

    cache.set("items:list", json.dumps(items), ex=60)
    return items


@app.get("/")
def index():
    items = fetch_items()
    return render_template(
        "index.html",
        items=items,
        person_name="khalil Sebouai",
        year="2026",
        study_model="Cloud",
    )


@app.post("/items")
def add_item():
    text = request.form.get("text", "").strip()
    if text:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO items (text) VALUES (%s)", (text,))
        cache.delete("items:list")

    return redirect(url_for("index"))


@app.get("/health")
def health():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        cache.ping()
        return {"status": "ok"}, 200
    except Exception as error:
        return {"status": "error", "detail": str(error)}, 500


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8000)
