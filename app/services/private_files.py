"""Bounded, private storage helpers for learning-resource files."""

from __future__ import annotations

import os
import re
import secrets
from pathlib import Path

MAX_PRIVATE_FILE_BYTES = 50 * 1024 * 1024
_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def private_dir() -> Path:
    configured = os.environ.get("CC_PRIVATE_UPLOAD_DIR", "")
    root = (
        Path(configured).expanduser()
        if configured
        else Path(__file__).resolve().parent.parent / ".private_resources"
    )
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    return root


def validate_filename(filename: str) -> str:
    if not isinstance(filename, str) or not _FILENAME.fullmatch(filename):
        raise ValueError("Invalid private filename.")
    path = Path(filename)
    if path.name != filename or path.is_absolute() or filename in {".", ".."}:
        raise ValueError("Invalid private filename.")
    return filename


def private_path(filename: str) -> Path:
    safe = validate_filename(filename)
    root = private_dir().resolve()
    path = (root / safe).resolve()
    if path.parent != root or path.is_symlink():
        raise ValueError("Invalid private path.")
    return path


def write_private(filename: str, data: bytes) -> None:
    path = private_path(filename)
    if (
        not isinstance(data, bytes)
        or not data
        or len(data) > MAX_PRIVATE_FILE_BYTES
    ):
        raise ValueError("File must contain 1 byte to 50 MB.")
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_private(filename: str) -> bytes:
    path = private_path(filename)
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError("Private file unavailable.")
    if path.stat().st_size > MAX_PRIVATE_FILE_BYTES:
        raise ValueError("Private file exceeds size limit.")
    data = path.read_bytes()
    if len(data) > MAX_PRIVATE_FILE_BYTES:
        raise ValueError("Private file exceeds size limit.")
    return data


def delete_private(filename: str) -> None:
    private_path(filename).unlink(missing_ok=True)


def download_filename(title: str, stored_filename: str) -> str:
    validate_filename(stored_filename)
    suffix = Path(stored_filename).suffix.lower()
    stem = (
        re.sub(r"[^A-Za-z0-9]+", "-", title.strip()).strip("-")[:80]
        or "resource"
    )
    return validate_filename(f"{stem}{suffix}")
