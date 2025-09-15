import libcst as cst
from splurge_unittest_to_pytest.stages.decorator_and_mock_fixes import DecoratorAndMockTransformer

DOMAINS = ["mocks", "stages"]


def _apply_transform(src: str) -> str:
    mod = cst.parse_module(src)
    new = mod.visit(DecoratorAndMockTransformer())
    return new.code


def test_mock_import_rewrite():
    src = """from unittest.mock import patch, MagicMock, side_effect\n"""
    out = _apply_transform(src)
    assert "import unittest.mock as mock" in out
    # side_effect should not be present as a from-import
    assert "side_effect" not in out.splitlines()[0]


def test_unittest_decorator_to_pytest_mark():
    src = """@unittest.skip('reason')\ndef test_foo():\n    pass\n\n@unittest.expectedFailure\ndef test_bar():\n    pass\n"""
    out = _apply_transform(src)
    assert "pytest.mark.skip" in out
    assert "pytest.mark.xfail" in out


def test_skipif_and_skipunless_and_name_variants():
    src = """@unittest.skipIf(True, 'nope')\ndef test_a():\n    pass\n\n@unittest.skipUnless(False, reason='why')\ndef test_b():\n    pass\n\n@expectedFailure\ndef test_c():\n    pass\n"""
    out = _apply_transform(src)
    assert "pytest.mark.skipif" in out
    assert "reason='why'" in out or "reason =" in out
    assert "pytest.mark.xfail" in out


def test_mock_import_alias_and_multiline():
    src = """from unittest.mock import (\n    patch as p,\n    MagicMock,\n    side_effect,\n)\n"""
    out = _apply_transform(src)
    # should import mock as module
    assert "import unittest.mock as mock" in out
    # alias p should be preserved in from-import (as p) or as import
    assert "patch" in out
