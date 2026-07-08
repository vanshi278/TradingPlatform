"""Password hashing (bcrypt) and JWT issue/verify."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from api.config import settings

ALGO = "HS256"


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_token(user_id: int, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_ttl_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGO)


def decode_token(token: str) -> dict:
    """Return the payload; raises jwt.InvalidTokenError (incl. expiry) on failure."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGO])
