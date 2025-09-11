import sys
from pathlib import Path
import subprocess

from splurge_unittest_to_pytest.main import convert_file


def _write_converted(src_path: Path, out_dir: Path) -> Path:
    result = convert_file(str(src_path))
    assert result.has_changes
    out_path = out_dir / (src_path.stem + "_converted.py")
    out_path.write_text(result.converted_code, encoding="utf-8")
    return out_path


def test_convert_and_pytest_collection(tmp_path: Path) -> None:
    """Convert a couple of example unittest files and run pytest collection/execution on them."""
    data_dir = Path(__file__).parents[2] / "data"
    # Pick a small sample of files to keep the test fast
    candidates = [
        "unittest_01.txt",
        "unittest_06.txt",
        "unittest_21.txt",
    ]

    sample_files = [data_dir / name for name in candidates if (data_dir / name).exists()]
    if not sample_files:
        # Nothing to do in this environment
        return

    out_dir = tmp_path / "converted"
    out_dir.mkdir()

    converted_paths = []
    for src in sample_files:
        converted_paths.append(_write_converted(src, out_dir))

    # Run pytest on the converted directory to ensure collection and simple execution succeed
    # Use -q and stop after first failure to keep CI feedback fast
    cmd = [sys.executable, "-m", "pytest", "-q", str(out_dir)]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    # If pytest fails, surface output for debugging
    assert proc.returncode == 0, f"pytest failed on converted files:\n{proc.stdout}"
