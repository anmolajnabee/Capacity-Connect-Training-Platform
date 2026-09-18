"""Standard-library password hashing, token hashing and session signing."""

from __future__ import annotations

import reflex as rx
import time
import base64
import hashlib
import hmac
import os
import secrets
import logging
import io
import zipfile
import re
from urllib.parse import urlsplit
from xml.etree import ElementTree


async def validate_role(state: rx.State, role: str) -> int:
    """Authorize every workspace operation from the signed cookie and live user."""
    from app.states.auth_state import AuthState
    from app.models import User
    from sqlalchemy import select

    try:
        auth = await state.get_state(AuthState)
        uid = read_session(auth.session_cookie)
        if uid <= 0 or role not in {"trainee", "trainer", "admin"}:
            return 0
        async with rx.asession() as session:
            return int(
                await session.scalar(
                    select(User.id).where(
                        User.id == uid,
                        User.role == role,
                        User.is_active.is_(True),
                        User.approval_status == "approved",
                    )
                )
                or 0
            )
    except Exception as e:
        logging.exception(f"Error: {type(e).__name__}")
        return 0


def valid_resource_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        return bool(
            0 < len(value) <= 500
            and parsed.scheme == "https"
            and not parsed.username
            and not parsed.password
            and not any(c.isspace() or ord(c) < 32 for c in value)
            and "\\" not in value
            and "." in host
            and all(
                re.fullmatch(
                    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", part
                )
                for part in host.split(".")
            )
            and (parsed.port is None or 1 <= parsed.port <= 65535)
        )
    except ValueError as e:
        logging.exception(f"Error: {type(e).__name__}")
        return False


def validate_resource_content(data: bytes, suffix: str) -> str:
    """Bounded format validation, not a malware-scanning guarantee."""
    if not data or len(data) > 50 * 1024 * 1024:
        raise ValueError("File must contain 1 byte to 50 MB.")
    if suffix in {".txt", ".md", ".csv"}:
        text = data.decode("utf-8-sig")
        if "\x00" in text or any(
            ord(c) < 32 and c not in "\r\n\t" for c in text
        ):
            raise ValueError("Text contains binary control characters.")
        return {
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".csv": "text/csv",
        }[suffix]
    if (
        suffix == ".pdf"
        and data.startswith(b"%PDF-")
        and b"%%EOF" in data[-2048:]
    ):
        return "application/pdf"
    if suffix == ".mp4":
        pos, kinds = 0, set()
        while pos + 8 <= len(data):
            size = int.from_bytes(data[pos : pos + 4], "big")
            kind = data[pos + 4 : pos + 8]
            header = 8
            if size == 1:
                size = int.from_bytes(data[pos + 8 : pos + 16], "big")
                header = 16
            if size == 0:
                size = len(data) - pos
            if size < header or pos + size > len(data):
                raise ValueError("Invalid MP4 box structure.")
            if kind == b"ftyp" and data[pos + 8 : pos + 12] not in {
                b"isom",
                b"iso2",
                b"mp41",
                b"mp42",
                b"avc1",
                b"dash",
                b"M4V ",
            }:
                raise ValueError("Unsupported MP4 brand.")
            kinds.add(kind)
            pos += size
        if pos == len(data) and {b"ftyp", b"moov", b"mdat"} <= kinds:
            return "video/mp4"
    if (
        suffix == ".webm"
        and data.startswith(b"\x1aE\xdf\xa3")
        and b"\x42\x82\x84webm" in data[:4096]
        and b"\x18\x53\x80\x67" in data[:8192]
    ):
        return "video/webm"
    office = {
        ".docx": ("word/document.xml", "wordprocessingml.document"),
        ".pptx": ("ppt/presentation.xml", "presentationml.presentation"),
        ".xlsx": ("xl/workbook.xml", "spreadsheetml.sheet"),
    }
    if suffix in office and data.startswith(b"PK\x03\x04"):
        main, mime = office[suffix]
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            names = {e.filename for e in entries}
            if (
                len(entries) > 2000
                or len(names) != len(entries)
                or sum(e.file_size for e in entries) > 100 * 1024 * 1024
            ):
                raise ValueError("Office archive exceeds safety limits.")
            if not {"[Content_Types].xml", "_rels/.rels", main} <= names:
                raise ValueError(
                    "Office document structure does not match its extension."
                )
            for entry in entries:
                if (
                    entry.flag_bits & 1
                    or ".." in entry.filename.split("/")
                    or entry.filename.startswith("/")
                    or "\\" in entry.filename
                    or any(
                        x in entry.filename.lower()
                        for x in ("vbaproject", "activex", "embeddings/")
                    )
                ):
                    raise ValueError("Unsafe Office document content.")
            for name in ("[Content_Types].xml", "_rels/.rels", main):
                info = archive.getinfo(name)
                if info.file_size > 10 * 1024 * 1024:
                    raise ValueError("Office XML exceeds safety limits.")
                xml = archive.read(name)
                if b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
                    raise ValueError("Unsafe XML declarations.")
                ElementTree.fromstring(xml)
            types = archive.read("[Content_Types].xml")
            if b"macroEnabled" in types or main.encode() not in types:
                raise ValueError("Office content types do not match.")
            return f"application/vnd.openxmlformats-officedocument.{mime}"
    raise ValueError("File content does not match an allowed format.")


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
