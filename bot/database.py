"""
IxlosJarimabot — SQLite ma'lumotlar bazasi bilan ishlash moduli.
Barcha jadvallar va yordamchi funksiyalar shu yerda.
"""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, date, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "jarimabot.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(super_admin_ids=None):
    """Bazani va jadvallarni yaratadi (agar mavjud bo'lmasa)."""
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS teachers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                position TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS fine_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                amount INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS fines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
                fine_type_id INTEGER NOT NULL REFERENCES fine_types(id) ON DELETE CASCADE,
                amount INTEGER NOT NULL,
                comment TEXT DEFAULT '',
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS admins (
                chat_id INTEGER PRIMARY KEY,
                full_name TEXT DEFAULT '',
                is_super INTEGER NOT NULL DEFAULT 0,
                added_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                full_name TEXT DEFAULT '',
                username TEXT DEFAULT '',
                first_seen TEXT NOT NULL
            );
            """
        )
        if super_admin_ids:
            for cid in super_admin_ids:
                conn.execute(
                    """INSERT INTO admins (chat_id, full_name, is_super, added_at)
                       VALUES (?, '', 1, ?)
                       ON CONFLICT(chat_id) DO UPDATE SET is_super=1""",
                    (cid, datetime.utcnow().isoformat()),
                )


# ---------------------------------------------------------------- users
def upsert_user(chat_id: int, full_name: str, username: str = ""):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO users (chat_id, full_name, username, first_seen)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(chat_id) DO UPDATE SET full_name=excluded.full_name, username=excluded.username""",
            (chat_id, full_name, username, datetime.utcnow().isoformat()),
        )


# ---------------------------------------------------------------- admins
def is_admin(chat_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM admins WHERE chat_id=?", (chat_id,)).fetchone()
        return row is not None


def is_super_admin(chat_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM admins WHERE chat_id=? AND is_super=1", (chat_id,)).fetchone()
        return row is not None


def add_admin(chat_id: int, full_name: str = "", is_super: bool = False):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO admins (chat_id, full_name, is_super, added_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(chat_id) DO UPDATE SET full_name=excluded.full_name, is_super=excluded.is_super""",
            (chat_id, full_name, int(is_super), datetime.utcnow().isoformat()),
        )


def remove_admin(chat_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM admins WHERE chat_id=? AND is_super=0", (chat_id,))


def list_admins():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM admins ORDER BY is_super DESC, added_at").fetchall()]


# ---------------------------------------------------------------- teachers
def add_teacher(full_name: str, position: str = "", phone: str = ""):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO teachers (full_name, position, phone, active, created_at) VALUES (?,?,?,1,?)",
            (full_name, position, phone, datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def update_teacher(teacher_id: int, full_name: str = None, position: str = None, phone: str = None, active: int = None):
    fields, values = [], []
    for col, val in (("full_name", full_name), ("position", position), ("phone", phone), ("active", active)):
        if val is not None:
            fields.append(f"{col}=?")
            values.append(val)
    if not fields:
        return
    values.append(teacher_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE teachers SET {', '.join(fields)} WHERE id=?", values)


def delete_teacher(teacher_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE teachers SET active=0 WHERE id=?", (teacher_id,))


def list_teachers(only_active=True):
    with get_conn() as conn:
        q = "SELECT * FROM teachers"
        if only_active:
            q += " WHERE active=1"
        q += " ORDER BY full_name"
        return [dict(r) for r in conn.execute(q).fetchall()]


def get_teacher(teacher_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM teachers WHERE id=?", (teacher_id,)).fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------- fine types
def add_fine_type(name: str, amount: int):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO fine_types (name, amount, active, created_at) VALUES (?,?,1,?)",
            (name, amount, datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def update_fine_type(ft_id: int, name: str = None, amount: int = None, active: int = None):
    fields, values = [], []
    for col, val in (("name", name), ("amount", amount), ("active", active)):
        if val is not None:
            fields.append(f"{col}=?")
            values.append(val)
    if not fields:
        return
    values.append(ft_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE fine_types SET {', '.join(fields)} WHERE id=?", values)


def delete_fine_type(ft_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE fine_types SET active=0 WHERE id=?", (ft_id,))


def list_fine_types(only_active=True):
    with get_conn() as conn:
        q = "SELECT * FROM fine_types"
        if only_active:
            q += " WHERE active=1"
        q += " ORDER BY name"
        return [dict(r) for r in conn.execute(q).fetchall()]


def get_fine_type(ft_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM fine_types WHERE id=?", (ft_id,)).fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------- fines
def add_fine(teacher_id: int, fine_type_id: int, amount: int, created_by: int, comment: str = ""):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO fines (teacher_id, fine_type_id, amount, comment, created_by, created_at)
               VALUES (?,?,?,?,?,?)""",
            (teacher_id, fine_type_id, amount, comment, created_by, datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def delete_fine(fine_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM fines WHERE id=?", (fine_id,))


def get_fine(fine_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM fines WHERE id=?", (fine_id,)).fetchone()
        return dict(row) if row else None


def update_fine(fine_id: int, teacher_id: int = None, fine_type_id: int = None,
                 amount: int = None, comment: str = None):
    fields, values = [], []
    for col, val in (("teacher_id", teacher_id), ("fine_type_id", fine_type_id),
                      ("amount", amount), ("comment", comment)):
        if val is not None:
            fields.append(f"{col}=?")
            values.append(val)
    if not fields:
        return
    values.append(fine_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE fines SET {', '.join(fields)} WHERE id=?", values)


def get_fines_between(start_dt: datetime, end_dt: datetime):
    """start_dt (inklyuziv), end_dt (eksklyuziv) oralig'idagi barcha jarimalar, teacher/fine_type nomlari bilan."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT f.id, f.amount, f.comment, f.created_at, f.created_by,
                   t.full_name AS teacher_name, t.position AS teacher_position,
                   ft.name AS fine_type_name
            FROM fines f
            JOIN teachers t ON t.id = f.teacher_id
            JOIN fine_types ft ON ft.id = f.fine_type_id
            WHERE f.created_at >= ? AND f.created_at < ?
            ORDER BY f.created_at DESC
            """,
            (start_dt.isoformat(), end_dt.isoformat()),
        ).fetchall()
        return [dict(r) for r in rows]


def get_recent_fines(limit=20):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT f.id, f.amount, f.comment, f.created_at,
                   f.teacher_id, f.fine_type_id,
                   t.full_name AS teacher_name, ft.name AS fine_type_name
            FROM fines f
            JOIN teachers t ON t.id = f.teacher_id
            JOIN fine_types ft ON ft.id = f.fine_type_id
            ORDER BY f.created_at DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def summary_by_teacher(start_dt: datetime, end_dt: datetime):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT t.full_name AS teacher_name, COUNT(f.id) AS cnt, COALESCE(SUM(f.amount),0) AS total
            FROM teachers t
            LEFT JOIN fines f ON f.teacher_id = t.id AND f.created_at >= ? AND f.created_at < ?
            WHERE t.active = 1
            GROUP BY t.id
            ORDER BY total DESC
            """,
            (start_dt.isoformat(), end_dt.isoformat()),
        ).fetchall()
        return [dict(r) for r in rows]
