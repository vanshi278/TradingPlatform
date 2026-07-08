"""User persistence + authentication against the `users` table."""
from __future__ import annotations

from typing import Optional

import psycopg2

from auth.security import hash_password, verify_password
from data.storage import get_conn


class EmailTaken(Exception):
    pass


def create_user(email: str, password: str) -> dict:
    email = email.strip().lower()
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (email, hashed_password) VALUES (%s, %s) "
                "RETURNING id, email, created_at",
                (email, hash_password(password)),
            )
            uid, em, created = cur.fetchone()
    except psycopg2.errors.UniqueViolation as exc:
        raise EmailTaken(email) from exc
    return {"id": uid, "email": em, "created_at": str(created)}


def get_user_by_email(email: str) -> Optional[dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, email, hashed_password, created_at FROM users WHERE email = %s",
            (email.strip().lower(),),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {"id": row[0], "email": row[1], "hashed_password": row[2], "created_at": str(row[3])}


def get_user_by_id(user_id: int) -> Optional[dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, email, created_at FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
    if not row:
        return None
    return {"id": row[0], "email": row[1], "created_at": str(row[2])}


def authenticate(email: str, password: str) -> Optional[dict]:
    """Return the public user dict when credentials are valid, else None."""
    user = get_user_by_email(email)
    if not user or not verify_password(password, user["hashed_password"]):
        return None
    return {"id": user["id"], "email": user["email"], "created_at": user["created_at"]}
