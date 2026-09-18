"""Standard-library password hashing, token hashing and session signing."""

from __future__ import annotations

import reflex as rx
import time
import base64
import hashlib
import hmac
import os
import secrets

PBKDF2_ALGORITHM = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 240_000
SESSION_LIFETIME = 60 * 60 * 24 * 7


def _session_key() -> bytes:
    explicit = os.environ.get("CC_SESSION_SECRET", "")
    if explicit:
        return explicit.encode()
    managed = os.environ.get("REFLEX_DB_URL", "")
    if not managed:
        raise RuntimeError(
            "A server-managed session signing secret is required."
        )
    return hmac.new(
        managed.encode(), b"capacity-connect/session-signing/v2", hashlib.sha256
    ).digest()


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def generate_salt() -> str:
    return _b64(secrets.token_bytes(16))


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Return (password_hash, salt) using PBKDF2-HMAC-SHA256."""
    use_salt = salt or generate_salt()
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        use_salt.encode(),
        PBKDF2_ITERATIONS,
    )
    return _b64(digest), use_salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Constant-time password verification."""
    if not password or not password_hash or not salt:
        return False
    candidate, _ = hash_password(password, salt)
    return hmac.compare_digest(candidate, password_hash)


def generate_reset_token() -> tuple[str, str]:
    """Return (plain_token, token_hash). Only the hash is persisted."""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def hash_token(token: str) -> str:
    return hashlib.sha256(f"cc-reset:{token}".encode()).hexdigest()


def sign_session(user_id: int) -> str:
    payload = f"{int(user_id)}.{int(time.time())}"
    signature = hmac.new(
        _session_key(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return f"{payload}.{signature}"


def read_session(cookie_value: str) -> int:
    """Return the user id from a signed cookie, or 0 when invalid."""
    if not cookie_value or len(cookie_value) > 128:
        return 0
    parts = cookie_value.split(".")
    if len(parts) != 3:
        return 0
    uid, issued, signature = parts
    if (
        not uid.isascii()
        or not issued.isascii()
        or not uid.isdigit()
        or not issued.isdigit()
        or len(uid) > 18
        or len(issued) > 12
    ):
        return 0
    age = int(time.time()) - int(issued)
    if int(uid) <= 0 or age < 0 or age >= SESSION_LIFETIME:
        return 0
    if len(signature) != 64 or not all(
        c in "0123456789abcdef" for c in signature
    ):
        return 0
    payload = f"{uid}.{issued}"
    expected = hmac.new(
        _session_key(), payload.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return 0
    return int(uid)


def password_problem(password: str, confirm: str) -> str:
    """Return an empty string when the password pair is acceptable."""
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if password.lower() == password or password.upper() == password:
        return "Password must mix upper and lower case letters."
    if not any(character.isdigit() for character in password):
        return "Password must contain at least one number."
    if password != confirm:
        return "Passwords do not match."
    return ""
