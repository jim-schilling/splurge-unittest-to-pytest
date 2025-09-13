import libcst as cst

from splurge_unittest_to_pytest.stages.pipeline import run_pipeline


def test_strict_mode_drops_classes_and_autouse():
    src = """
import unittest

class TestX(unittest.TestCase):
    def setUp(self):
        self.x = 1

    def tearDown(self):
        self.x = None

    def test_a(self):
        assert self.x == 1
"""
    mod = cst.parse_module(src)
    out = run_pipeline(mod, compat=False, autocreate=False)
    code = out.code
    # Class should be removed in strict mode
    assert "class TestX" not in code
    # Autouse attach fixture should not be present
    assert "def _attach_to_instance(" not in code
    # Top-level pytest test should exist
    assert "def test_a(" in code

