from pathlib import Path

from splurge_unittest_to_pytest.main import convert_string
from tests.support.golden_compare import assert_code_equal


def test_sample_06_matches_golden():
    sample = Path(__file__).parents[1] / "data" / "samples" / "sample-06-unittest.txt"
    src = sample.read_text()
    res = convert_string(src)
    converted = res.converted_code
    golden = (Path(__file__).parents[1] / "data" / "goldens" / "sample_06_converted.expected").read_text()
    # ensure at least one test function exists in converted output
    assert "def test_" in converted
    # golden AST-based comparison (robust to formatting)
    ok, msg = assert_code_equal(converted, golden)
    assert ok, msg
