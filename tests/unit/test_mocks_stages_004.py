import libcst as cst
from splurge_unittest_to_pytest.stages.decorator_and_mock_fixes import DecoratorAndMockTransformer

DOMAINS = ["mocks", "stages"]


def _apply(src: str) -> str:
    mod = cst.parse_module(src)
    new = mod.visit(DecoratorAndMockTransformer())
    return new.code


def test_mock_from_import_rewrite_with_autospec_and_side_effect():
    src = """
from unittest.mock import Mock, autospec, side_effect, patch

class T:
    def test(self):
        m = Mock()
        m.side_effect = lambda: None
"""
    out = _apply(src)
    # should have imported unittest.mock as mock when unknown names present
    assert "import unittest.mock as mock" in out or "from unittest.mock import Mock" in out
    # side_effect should not remain as a from-import name
    assert "side_effect" not in out.splitlines()[0]
