from __future__ import annotations

import os
from pathlib import Path

import pytest

from splurge_unittest_to_pytest.io_helpers import atomic_write, safe_file_writer


def test_atomic_write_text_and_bytes(tmp_path: Path) -> None:
    p = tmp_path / "foo.txt"
    # write text with explicit encoding
    atomic_write(p, "hello", encoding="utf-8")
    assert p.exists()
    assert p.read_text(encoding="utf-8") == "hello"

    # overwrite with bytes
    atomic_write(p, b"bye")
    assert p.read_bytes() == b"bye"


def test_atomic_write_requires_encoding_for_text(tmp_path: Path) -> None:
    p = tmp_path / "bar.txt"
    with pytest.raises(ValueError):
        atomic_write(p, "text without encoding", encoding=None)


def test_safe_file_writer_rejects_root(tmp_path: Path, monkeypatch) -> None:
    # On platforms where resolving to root is tricky, emulate an unsafe path
    root = Path("/")
    # If running on Windows, use C:\ as root
    if os.name == "nt":
        root = Path(os.environ.get("SYSTEMROOT", "C:\\"))

    with pytest.raises(ValueError):
        # safe_file_writer should refuse obvious system roots
        _ = safe_file_writer(root / "forbidden.txt")
