"""I/O helpers used by the conversion tool.

This module provides a small set of helpers for safe file writes and
encoding detection used by ``splurge_unittest_to_pytest``.

Copyright (c) 2025 Jim Schilling
License: MIT
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from .types import TextWriterProtocol
import os
from uuid import uuid4

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


def safe_file_writer(path: Path, *, encoding: str = "utf-8") -> TextWriterProtocol:
    """Open a file for writing NDJSON safely.

    This helper performs a small set of safety checks and opens the file
    for writing with the requested encoding. It rejects obvious system
    locations (for example Windows system directories and root paths)
    to avoid accidental overwrites of sensitive files.

    The returned object behaves like a normal file object opened for
    writing (text mode). The caller is responsible for closing it, or
    using the object as a context manager.

    Safety checks (best-effort):
      - Rejects paths that resolve to a system root (parent == self).
      - Rejects known Windows system directories ("Windows", "Windows\\System32").
      - Rejects paths inside OS installation directories as inferred from
        environment variables like %WINDIR% or %SYSTEMROOT%.

    Args:
        path: Destination path to open for writing.
        encoding: Text encoding to use (default: "utf-8").

    Returns:
        An open file object in text write mode.

    Raises:
        PermissionError: If writing to the path is not permitted.
        ValueError: If the path is considered unsafe.
        OSError: For other IO-related errors.
    """
    # Resolve the path where possible
    try:
        resolved = path.resolve()
    except Exception:
        # If resolution fails, fall back to the input path
        resolved = path

    # Reject root-like targets (e.g., C:\ or /)
    try:
        if resolved.parent == resolved:
            raise ValueError(f"Refusing to write to root path: {resolved}")
    except Exception:
        # If we cannot determine parent reliably, be conservative and reject
        raise ValueError(f"Refusing to write to uncertain path: {path}")

    # Reject common Windows system locations by checking components and env vars
    name_parts = [p.lower() for p in resolved.parts]
    if any(part in ("windows", "windows\\system32", "system32") for part in name_parts):
        raise ValueError(f"Refusing to write to Windows system directory: {resolved}")

    # Reject common UNIX-like system directories
    unix_blacklist = {"/", "/etc", "/bin", "/usr", "/boot", "/sbin", "/lib", "/root", "/var"}
    try:
        # Build a normalized absolute path and check for containment
        resolved_str = str(resolved)
        for forbidden in unix_blacklist:
            if resolved_str == forbidden or resolved_str.startswith(forbidden + os.sep):
                raise ValueError(f"Refusing to write to system directory: {resolved}")
    except Exception:
        # If something about path handling failed, be conservative and continue to other checks
        pass

    # If WINDIR or SYSTEMROOT env vars exist, ensure we don't write into them
    for ev in ("WINDIR", "SYSTEMROOT"):
        val = os.environ.get(ev)
        if val:
            try:
                rv = Path(val).resolve()
                if rv in resolved.parents or rv == resolved:
                    raise ValueError(f"Refusing to write inside system directory ({ev}): {resolved}")
            except Exception:
                # If resolution fails, ignore and continue
                pass

    # Ensure parent dir exists
    resolved.parent.mkdir(parents=True, exist_ok=True)

    # Provide an atomic temp-file writer which writes into a temporary
    # file in the same directory and then replaces the destination on
    # close. This avoids partial files if the process is interrupted.
    tmp_name = f"{resolved.name}.tmp-{uuid4().hex}"
    tmp_path = resolved.with_name(tmp_name)

    class _AtomicTextWriter:
        def __init__(self, final: Path, tmp: Path, enc: str):
            self._final = final
            self._tmp = tmp
            self._enc = enc
            # Open tmp file for writing text
            self._fp = tmp.open("w", encoding=enc)

        def write(self, data: str) -> int:
            return self._fp.write(data)

        def writelines(self, lines) -> None:
            return self._fp.writelines(lines)

        def flush(self) -> None:
            return self._fp.flush()

        def close(self) -> None:
            try:
                self._fp.close()
                # Replace final path atomically
                self._tmp.replace(self._final)
            except Exception:
                # Attempt to remove tmp file if something went wrong
                try:
                    if self._tmp.exists():
                        self._tmp.unlink()
                except Exception:
                    pass
                raise

        # Context manager support
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            # If exception occurred, ensure tmp is cleaned up
            if exc_type is not None:
                try:
                    if self._tmp.exists():
                        self._tmp.unlink()
                except Exception:
                    pass
                return False
            self.close()
            return True

    return _AtomicTextWriter(resolved, tmp_path, encoding)
