import subprocess
import sys
from pathlib import Path


def test_print_diagnostics_finds_run(tmp_path: Path) -> None:
    # Create a fake diagnostics root
    root = tmp_path / "diag_root"
    root.mkdir()

    # Create a run dir
    run_dir = root / "splurge-diagnostics-2025-09-12_12-00-00"
    run_dir.mkdir()

    # Marker file
    marker = run_dir / "splurge-diagnostics-2025-09-12_12-00-00"
    marker.write_text(str(run_dir.resolve()), encoding="utf-8")

    # A sample snapshot file
    sample = run_dir / "test_snapshot.py"
    sample.write_text("x = 1", encoding="utf-8")

    # Run the helper script pointing at the root
    proc = subprocess.run(
        [sys.executable, "tools/print_diagnostics.py", "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )

    out = proc.stdout + proc.stderr
    assert "Diagnostics run directory" in out
    assert "splurge-diagnostics-2025-09-12_12-00-00" in out
    assert "test_snapshot.py" in out