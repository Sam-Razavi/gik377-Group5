"""
PostgreSQL-databas för persistent lagring av prenumeranter och skickade notifieringar.
Använder psycopg2 som driver. Anslutningsparametrar läses från config.py.
"""

import time
import psycopg2
from psycopg2.extras import RealDictCursor
from services.notification.config import (
    PG_HOST,
    PG_PORT,
    PG_DATABASE,
    PG_USER,
    PG_PASSWORD,
)


def _connect():
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DATABASE,
        user=PG_USER,
        password=PG_PASSWORD,
    )
    return conn


def init_db():
    """Skapar tabellerna om de inte redan finns."""
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                user_id TEXT PRIMARY KEY,
                phone TEXT,
                email TEXT
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS subscriber_sites (
                user_id TEXT NOT NULL,
                site_id TEXT NOT NULL,
                visited BOOLEAN NOT NULL DEFAULT FALSE,
                PRIMARY KEY (user_id, site_id),
                FOREIGN KEY (user_id) REFERENCES subscribers(user_id) ON DELETE CASCADE
            );
        """)
        cur.execute("""
            ALTER TABLE subscriber_sites
            ADD COLUMN IF NOT EXISTS visited BOOLEAN NOT NULL DEFAULT FALSE;
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sent_log (
                user_id TEXT NOT NULL,
                site_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                sent_at DOUBLE PRECISION NOT NULL,
                PRIMARY KEY (user_id, site_id, channel)
            );
        """)
    conn.commit()
    conn.close()


# --- Sent log (anti-spam) ---

def get_last_sent(user_id, site_id, channel):
    """Returnerar timestamp för senaste notifiering, eller 0."""
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT sent_at FROM sent_log WHERE user_id=%s AND site_id=%s AND channel=%s",
            (user_id, site_id, channel),
        )
        row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


def mark_sent(user_id, site_id, channel):
    """Registrerar att en notifiering har skickats."""
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO sent_log (user_id, site_id, channel, sent_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, site_id, channel)
            DO UPDATE SET sent_at = EXCLUDED.sent_at
            """,
            (user_id, site_id, channel, time.time()),
        )
    conn.commit()
    conn.close()


# --- Visited (besökta världsarv) ---

def is_visited(user_id, site_id):
    """Returnerar True om användaren har bockat av detta världsarv."""
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT visited FROM subscriber_sites WHERE user_id=%s AND site_id=%s",
            (user_id, site_id),
        )
        row = cur.fetchone()
    conn.close()
    return bool(row[0]) if row else False


def mark_visited(user_id, site_id):
    """Markerar ett världsarv som besökt. Returnerar True om raden uppdaterades."""
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE subscriber_sites SET visited=TRUE WHERE user_id=%s AND site_id=%s",
            (user_id, site_id),
        )
        updated = cur.rowcount
    conn.commit()
    conn.close()
    return updated > 0


# --- Prenumeranter ---

def add_subscriber(user_id, phone=None, email=None, sites=None):
    """Lägger till eller uppdaterar en prenumerant."""
    conn = _connect()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM subscribers WHERE user_id=%s", (user_id,))
        existing = cur.fetchone()

        if existing:
            if phone:
                cur.execute(
                    "UPDATE subscribers SET phone=%s WHERE user_id=%s",
                    (phone, user_id),
                )
            if email:
                cur.execute(
                    "UPDATE subscribers SET email=%s WHERE user_id=%s",
                    (email, user_id),
                )
        else:
            cur.execute(
                "INSERT INTO subscribers (user_id, phone, email) VALUES (%s, %s, %s)",
                (user_id, phone, email),
            )

        if sites:
            for site_id in sites:
                cur.execute(
                    """
                    INSERT INTO subscriber_sites (user_id, site_id)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id, site_id) DO NOTHING
                    """,
                    (user_id, site_id),
                )

        conn.commit()
        sub = _get_subscriber(cur, user_id)
    conn.close()
    return sub


def remove_subscriber(user_id, sites=None):
    """Tar bort prenumerant eller specifika platser."""
    conn = _connect()
    with conn.cursor() as cur:
        if sites:
            for site_id in sites:
                cur.execute(
                    "DELETE FROM subscriber_sites WHERE user_id=%s AND site_id=%s",
                    (user_id, site_id),
                )
        else:
            cur.execute("DELETE FROM subscriber_sites WHERE user_id=%s", (user_id,))
            cur.execute("DELETE FROM subscribers WHERE user_id=%s", (user_id,))
    conn.commit()
    conn.close()


def get_subscriber(user_id):
    """Hämtar en enskild prenumerant."""
    conn = _connect()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        sub = _get_subscriber(cur, user_id)
    conn.close()
    return sub


def get_all_subscribers():
    """Hämtar alla prenumeranter som dict."""
    conn = _connect()
    result = {}
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM subscribers")
        rows = cur.fetchall()
        for row in rows:
            uid = row["user_id"]
            cur.execute(
                "SELECT site_id FROM subscriber_sites WHERE user_id=%s", (uid,)
            )
            sites = [r["site_id"] for r in cur.fetchall()]
            result[uid] = {"phone": row["phone"], "email": row["email"], "sites": sites}
    conn.close()
    return result


def subscriber_exists(user_id):
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM subscribers WHERE user_id=%s", (user_id,))
        row = cur.fetchone()
    conn.close()
    return row is not None


def _get_subscriber(cur, user_id):
    """Intern hjälpfunktion - förväntar sig en cursor med RealDictCursor."""
    cur.execute("SELECT * FROM subscribers WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    if not row:
        return None
    cur.execute(
        "SELECT site_id FROM subscriber_sites WHERE user_id=%s", (user_id,)
    )
    sites = [r["site_id"] for r in cur.fetchall()]
    return {"phone": row["phone"], "email": row["email"], "sites": sites}
