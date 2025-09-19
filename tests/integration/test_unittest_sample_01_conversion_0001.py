from pathlib import Path
from splurge_unittest_to_pytest.main import convert_string
from tests.support.golden_compare import assert_code_equal


def test_unittest_01_a_converts_to_golden():
    samples_dir = Path(__file__).parents[1] / "data" / "unittest_pytest_samples"
    src = (samples_dir / "unittest_01_a.py.txt").read_text()
    res = convert_string(src)
    converted = res.converted_code
    golden = (samples_dir / "pytest_01.py.txt").read_text()
    # quick smoke: ensure the converted output contains a pytest test function
    assert "def test_" in converted
    ok, msg = assert_code_equal(converted, golden)
    assert ok, msg
