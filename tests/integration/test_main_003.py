import libcst as cst
from pathlib import Path
from splurge_unittest_to_pytest.main import convert_string

DOMAINS = ["main"]


def read_sample(n: int) -> str:
    p = Path(__file__).parents[1] / "data" / f"unittest_{n:02d}.txt"
    return p.read_text()


def test_pipeline_converts_sample_and_parses() -> None:
    src = read_sample(1)
    # run pipeline engine
    res = convert_string(src)
    assert res.converted_code
    # ensure converted code parses
    cst.parse_module(res.converted_code)
