"""
SQLite-databas för persistent lagring av prenumeranter och skickade notifieringar.
Inbyggt i Python via sqlite3 – ingen extern databasserver behövs.
"""

import sqlite3
import time
from services.notification.config import DB_PATH


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Skapar tabellerna om de inte redan finns."""
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id TEXT PRIMARY KEY,
            phone TEXT,
            email TEXT
        );

        CREATE TABLE IF NOT EXISTS subscriber_sites (
            user_id TEXT NOT NULL,
            site_id TEXT NOT NULL,
            PRIMARY KEY (user_id, site_id),
            FOREIGN KEY (user_id) REFERENCES subscribers(user_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS sent_log (
            user_id TEXT NOT NULL,
            site_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            sent_at REAL NOT NULL,
            PRIMARY KEY (user_id, site_id, channel)
        );
    """)
    conn.commit()
    conn.close()


# --- Sent log (anti-spam) ---

def get_last_sent(user_id, site_id, channel):
    """Returnerar timestamp för senaste notifiering, eller 0."""
    conn = _connect()
    row = conn.execute(
        "SELECT sent_at FROM sent_log WHERE user_id=? AND site_id=? AND channel=?",
        (user_id, site_id, channel),
    ).fetchone()
    conn.close()
    return row["sent_at"] if row else 0


def mark_sent(user_id, site_id, channel):
    """Registrerar att en notifiering har skickats."""
    conn = _connect()
    conn.execute(
        "INSERT OR REPLACE INTO sent_log (user_id, site_id, channel, sent_at) VALUES (?, ?, ?, ?)",
        (user_id, site_id, channel, time.time()),
    )
    conn.commit()
    conn.close()


# --- Prenumeranter ---

def add_subscriber(user_id, phone=None, email=None, sites=None):
    """Lägger till eller uppdaterar en prenumerant."""
    conn = _connect()
    existing = conn.execute("SELECT * FROM subscribers WHERE user_id=?", (user_id,)).fetchone()

    if existing:
        if phone:
            conn.execute("UPDATE subscribers SET phone=? WHERE user_id=?", (phone, user_id))
        if email:
            conn.execute("UPDATE subscribers SET email=? WHERE user_id=?", (email, user_id))
    else:
        conn.execute(
            "INSERT INTO subscribers (user_id, phone, email) VALUES (?, ?, ?)",
            (user_id, phone, email),
        )

    if sites:
        for site_id in sites:
            conn.execute(
                "INSERT OR IGNORE INTO subscriber_sites (user_id, site_id) VALUES (?, ?)",
                (user_id, site_id),
            )

    conn.commit()
    sub = _get_subscriber(conn, user_id)
    conn.close()
    return sub


def remove_subscriber(user_id, sites=None):
    """Tar bort prenumerant eller specifika platser."""
    conn = _connect()
    if sites:
        for site_id in sites:
            conn.execute(
                "DELETE FROM subscriber_sites WHERE user_id=? AND site_id=?",
                (user_id, site_id),
            )
    else:
        conn.execute("DELETE FROM subscriber_sites WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM subscribers WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def get_subscriber(user_id):
    """Hämtar en enskild prenumerant."""
    conn = _connect()
    sub = _get_subscriber(conn, user_id)
    conn.close()
    return sub


def get_all_subscribers():
    """Hämtar alla prenumeranter som dict."""
    conn = _connect()
    rows = conn.execute("SELECT * FROM subscribers").fetchall()
    result = {}
    for row in rows:
        uid = row["user_id"]
        sites = [r["site_id"] for r in conn.execute(
            "SELECT site_id FROM subscriber_sites WHERE user_id=?", (uid,)
        ).fetchall()]
        result[uid] = {"phone": row["phone"], "email": row["email"], "sites": sites}
    conn.close()
    return result


def subscriber_exists(user_id):
    conn = _connect()
    row = conn.execute("SELECT 1 FROM subscribers WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row is not None


def _get_subscriber(conn, user_id):
    row = conn.execute("SELECT * FROM subscribers WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        return None
    sites = [r["site_id"] for r in conn.execute(
        "SELECT site_id FROM subscriber_sites WHERE user_id=?", (user_id,)
    ).fetchall()]
    return {"phone": row["phone"], "email": row["email"], "sites": sites}
