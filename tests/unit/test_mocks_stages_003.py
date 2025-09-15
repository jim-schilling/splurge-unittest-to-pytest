from pathlib import Path
import json
import libcst as cst

from splurge_unittest_to_pytest.stages.decorator_and_mock_fixes import DecoratorAndMockTransformer

DOMAINS = ["mocks", "stages"]


def test_known_bad_mapping_loaded():
    # Verify the curated mapping file exists and contains 'side_effect'
    p = Path(__file__).parents[2] / "splurge_unittest_to_pytest" / "data" / "known_bad_mock_names.json"
    assert p.exists(), "known_bad_mock_names.json must exist"
    parsed = json.loads(p.read_text(encoding="utf8"))
    assert isinstance(parsed, dict)
    assert "side_effect" in parsed, "mapping should include 'side_effect'"


def test_transformer_rewrites_side_effect_import():
    src = "from unittest.mock import patch, MagicMock, side_effect\n"
    module = cst.parse_module(src)
    tr = DecoratorAndMockTransformer()
    new_mod = module.visit(tr)
    code = new_mod.code
    # Should not retain 'side_effect' in a from-import
    assert "side_effect" not in code.splitlines()[0]
    # Should have added an import for unittest.mock as mock
    assert any("import unittest.mock as mock" in line for line in code.splitlines())
