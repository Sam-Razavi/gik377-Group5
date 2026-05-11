"""
PostgreSQL storage for notification subscribers and sent notifications.
Falls back to in-memory storage when notification mock mode is active.
"""

import time

import psycopg2
from psycopg2.extras import RealDictCursor

from services.notification.config import (
    NOTIFICATION_MOCK_MODE,
    PG_DATABASE,
    PG_HOST,
    PG_PASSWORD,
    PG_PORT,
    PG_USER,
)

_mock_subscribers = {}
_mock_sent_log = {}
_mock_visited = set()


def _get_mock_subscriber(user_id):
    sub = _mock_subscribers.get(user_id)
    if not sub:
        return None
    return {
        "phone": sub.get("phone"),
        "email": sub.get("email"),
        "sites": list(sub.get("sites", [])),
    }


def _connect():
    if NOTIFICATION_MOCK_MODE:
        raise RuntimeError("Using notification mock mode - no DB connection")

    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DATABASE,
        user=PG_USER,
        password=PG_PASSWORD,
    )
    return conn


def init_db():
    """Create tables if they do not already exist."""
    if NOTIFICATION_MOCK_MODE:
        return

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


def get_last_sent(user_id, site_id, channel):
    """Return the latest sent timestamp, or 0."""
    if NOTIFICATION_MOCK_MODE:
        return _mock_sent_log.get((user_id, site_id, channel), 0)

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
    """Record that a notification was sent."""
    if NOTIFICATION_MOCK_MODE:
        _mock_sent_log[(user_id, site_id, channel)] = time.time()
        return

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


def is_visited(user_id, site_id):
    """Return True when the user has marked the site as visited."""
    if NOTIFICATION_MOCK_MODE:
        return (user_id, site_id) in _mock_visited

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
    """Mark a subscribed site as visited. Returns True if updated."""
    if NOTIFICATION_MOCK_MODE:
        sub = _mock_subscribers.get(user_id)
        if not sub or site_id not in sub.get("sites", []):
            return False
        _mock_visited.add((user_id, site_id))
        return True

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


def add_subscriber(user_id, phone=None, email=None, sites=None):
    """Add or update a subscriber."""
    if NOTIFICATION_MOCK_MODE:
        sub = _mock_subscribers.setdefault(
            user_id,
            {"phone": None, "email": None, "sites": []},
        )
        if phone:
            sub["phone"] = phone
        if email:
            sub["email"] = email
        if sites:
            for site_id in sites:
                if site_id not in sub["sites"]:
                    sub["sites"].append(site_id)
        return _get_mock_subscriber(user_id)

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
    """Remove a subscriber or selected subscribed sites."""
    if NOTIFICATION_MOCK_MODE:
        if user_id not in _mock_subscribers:
            return
        if sites:
            current_sites = _mock_subscribers[user_id].get("sites", [])
            _mock_subscribers[user_id]["sites"] = [
                site_id for site_id in current_sites if site_id not in sites
            ]
            for site_id in sites:
                _mock_visited.discard((user_id, site_id))
        else:
            del _mock_subscribers[user_id]
            for key in list(_mock_sent_log):
                if key[0] == user_id:
                    del _mock_sent_log[key]
            for visited_key in list(_mock_visited):
                if visited_key[0] == user_id:
                    _mock_visited.discard(visited_key)
        return

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
    """Fetch one subscriber."""
    if NOTIFICATION_MOCK_MODE:
        return _get_mock_subscriber(user_id)

    conn = _connect()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        sub = _get_subscriber(cur, user_id)
    conn.close()
    return sub


def get_all_subscribers():
    """Fetch all subscribers as a dict."""
    if NOTIFICATION_MOCK_MODE:
        return {
            user_id: _get_mock_subscriber(user_id)
            for user_id in _mock_subscribers
        }

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
    if NOTIFICATION_MOCK_MODE:
        return user_id in _mock_subscribers

    conn = _connect()
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM subscribers WHERE user_id=%s", (user_id,))
        row = cur.fetchone()
    conn.close()
    return row is not None


def _get_subscriber(cur, user_id):
    """Internal helper for a RealDictCursor."""
    cur.execute("SELECT * FROM subscribers WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    if not row:
        return None
    cur.execute(
        "SELECT site_id FROM subscriber_sites WHERE user_id=%s", (user_id,)
    )
    sites = [r["site_id"] for r in cur.fetchall()]
    return {"phone": row["phone"], "email": row["email"], "sites": sites}
