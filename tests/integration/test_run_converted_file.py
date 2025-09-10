import subprocess
from pathlib import Path
from splurge_unittest_to_pytest.main import convert_string


def test_convert_and_run_single_file(tmp_path: Path) -> None:
    src_path = Path(__file__).parents[1] / "data" / "unittest_01.txt"
    src = src_path.read_text()
    res = convert_string(src, compat=True, engine="pipeline")
    assert res.converted_code
    out_file = tmp_path / "converted.py"
    out_file.write_text(res.converted_code)
    # run pytest on the converted file
    proc = subprocess.run(["python", "-m", "pytest", "-q", str(out_file)], capture_output=True, text=True, cwd=str(tmp_path))
    # exit code 0 indicates tests passed
    assert proc.returncode == 0, proc.stderr + "\n" + proc.stdout
