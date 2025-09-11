from pathlib import Path
import libcst as cst

from splurge_unittest_to_pytest.main import convert_string


DATA_DIR = Path(__file__).parents[2] / "tests" / "data"
NEW_FILES = [
    "unittest_param_decorators_complex.txt",
    "unittest_mock_alias_edgecases.txt",
    "unittest_combined_complex.txt",
]


def test_convert_and_check_variants():
    for fname in NEW_FILES:
        p = DATA_DIR / fname
        src = p.read_text(encoding="utf8")
        res = convert_string(src, engine="pipeline", compat=True)
        code = getattr(res, "converted_code", None)
        assert code is not None, f"Conversion failed for {p}"
        # parse to ensure syntactically valid
        cst.parse_module(code)
        # sanity checks: no raw 'from unittest.mock import side_effect' remain
        assert "from unittest.mock import side_effect" not in code
        # ensure pytest marks are present when expected
        if "skipIf" in src or "skipUnless" in src:
            assert "pytest.mark.skipif" in code or "pytest.mark.skip" in code
