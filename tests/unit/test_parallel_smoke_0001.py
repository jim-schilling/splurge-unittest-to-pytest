from __future__ import annotations

from pathlib import Path
import threading
import os
import pytest

from splurge_unittest_to_pytest.io_helpers import atomic_write


def _worker(path: Path, content: bytes) -> None:
    # write bytes concurrently to ensure atomic_write replaces files cleanly
    atomic_write(path, content)


@pytest.mark.skipif(os.name == "nt", reason="Windows rename semantics make this concurrency test flaky")
def test_concurrent_atomic_writes(tmp_path: Path) -> None:
    p = tmp_path / "shared.bin"
    threads = []
    for i in range(5):
        t = threading.Thread(target=_worker, args=(p, bytes([i])))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    # ensure file exists and contains a single byte (one of the writes)
    assert p.exists()
    assert p.read_bytes() in {b"\x00", b"\x01", b"\x02", b"\x03", b"\x04"}
