"""I/O helpers used by the conversion tool.

This module provides a small set of helpers for safe file writes and
encoding detection used by ``splurge_unittest_to_pytest``.

Copyright (c) 2025 Jim Schilling
License: MIT
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

DOMAIN = ["io", "helpers"]


def atomic_write(
    path: Path,
    data: str | bytes,
    *,
    encoding: str | None = "utf-8",
) -> None:
    """Atomically write data to a file.

    The function writes data to a temporary file in the same directory and
    then renames/replaces the temporary file into the final destination.

    Args:
        path: The target file path to write.
        data: The content to write. If ``str``, the ``encoding`` argument must
            be provided. If ``bytes``, it is written directly.
        encoding: The text encoding to use when ``data`` is a string. If
            ``None`` and ``data`` is a ``str`` a ``ValueError`` is raised.

    Raises:
        ValueError: If ``data`` is a string and ``encoding`` is ``None``.
        PermissionError: If the process lacks permissions to write/replace
            the destination file.
        OSError: For other OS-level write/replace failures.
    """
    # Create parent dir if missing
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp = path.with_name(path.name + ".tmp")
    if isinstance(data, str):
        if encoding is None:
            raise ValueError("encoding must be provided when writing text")
        tmp.write_text(data, encoding=encoding)
    else:
        tmp.write_bytes(data)
    # Use replace so existing files are atomically swapped on most platforms
    tmp.replace(path)


def detect_encoding(path: Path) -> str:
    """Detect a reasonable text encoding for a file.

    The function attempts to read the file as UTF-8 first and falls back to
    Latin-1 if UTF-8 decoding fails. Returning ``latin-1`` preserves the
    raw bytes without raising on decode errors and is therefore safe for
    subsequent round-trip operations.

    Args:
        path: Path to the file to inspect.

    Returns:
        The name of the encoding to use (``"utf-8"`` or ``"latin-1"``).
    """
    try:
        path.read_text(encoding="utf-8")
        return "utf-8"
    except Exception:
        return "latin-1"


def hash_suffix_for_path(
    path: Path,
    *,
    length: int = 8,
) -> str:
    """Return a short SHA-256 hex suffix for the file contents or path.

    This helper returns a stable short hex suffix that can be used when
    creating backup filenames. If the file exists its contents are hashed;
    otherwise the stringified path is used as a fallback.

    Args:
        path: File path whose contents (or name) are used to compute the hash.
        length: Number of hex characters to return from the hash digest.

    Returns:
        A lowercase hex string of up to ``length`` characters.
    """
    try:
        data = path.read_bytes()
    except Exception:
        data = str(path).encode("utf-8")
    h = sha256(data).hexdigest()
    return h[:length]
