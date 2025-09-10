import tempfile
import textwrap
import libcst as cst
from pathlib import Path
from splurge_unittest_to_pytest.main import convert_string


def read_sample(n: int) -> str:
    p = Path(__file__).parents[1] / "data" / f"unittest_{n:02d}.txt"
    return p.read_text()


def test_pipeline_converts_sample_and_parses():
    src = read_sample(1)
    # run pipeline engine
    res = convert_string(src, compat=True, engine="pipeline")
    assert res.converted_code
    # ensure converted code parses
    cst.parse_module(res.converted_code)
