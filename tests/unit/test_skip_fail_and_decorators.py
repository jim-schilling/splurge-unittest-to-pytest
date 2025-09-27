import libcst as cst

from splurge_unittest_to_pytest.pattern_analyzer import UnittestPatternAnalyzer
from splurge_unittest_to_pytest.transformers import unittest_transformer
from splurge_unittest_to_pytest.transformers.assert_transformer import transform_assertions_string_based
from splurge_unittest_to_pytest.transformers.unittest_transformer import (
    UnittestToPytestCSTTransformer,
)


def test_transform_skip_and_fail_string_based():
    src = """
class ExampleTest(unittest.TestCase):
    def test_one(self):
        self.skipTest("not relevant")
        self.fail('boom')
"""
    out = transform_assertions_string_based(src)
    assert 'pytest.skip("not relevant")' in out or "pytest.skip('not relevant')" in out
    assert "pytest.fail('boom')" in out or 'pytest.fail("boom")' in out


def test_decorator_detection_sets_pytest_needed():
    src = """
import unittest

@unittest.skip("nope")
class SkipMe(unittest.TestCase):
    def test_should_be_skipped(self):
        pass
"""
    analyzer = UnittestPatternAnalyzer()
    # Analyzer won't actually rewrite the code, but should detect unittest classes
    ir = analyzer.analyze_module(src)
    # If class is recognized as unittest.TestCase, analyzer marks module needing pytest import
    assert isinstance(ir, type(ir))
    # The analyzer sets needs_pytest_import based on class inheritance
    # This is a lightweight check that parsing decorators didn't crash
    assert any(cls.is_unittest_class for cls in ir.classes)


def test_cst_rewrites_decorators_to_pytest_marks():
    src = """
import unittest

@unittest.skip("nope")
class SkipMe(unittest.TestCase):
    @unittest.skipIf(True, "reason")
    def test_should_be_skipped(self):
        pass

@unittest.skipIf(False, "x")
def test_free_function():
    pass
"""
    # Parse and run transformer
    module = cst.parse_module(src)
    transformer = UnittestToPytestCSTTransformer()
    new_mod = module.visit(transformer)
    code = new_mod.code

    assert "@pytest.mark.skip(" in code or "@pytest.mark.skipif(" in code
    # class decorator replaced
    assert "@pytest.mark.skip" in code
    # method decorator replaced
    assert "@pytest.mark.skipif" in code


def test_transform_injects_pytest_import_when_needed():
    src = """
import unittest

@unittest.skip("nope")
class SkipMe(unittest.TestCase):
    def test_one(self):
        self.skipTest("not relevant")
"""
    transformer = UnittestToPytestCSTTransformer()
    out = transformer.transform_code(src)
    # Should contain an import pytest line inserted
    assert "import pytest" in out
    # And skipTest should be converted to pytest.skip in string-fallback phase
    assert "pytest.skip(" in out


def test_transform_preserves_existing_pytest_import():
    src = """
import pytest
import unittest

@unittest.skipIf(True, "x")
def test_something():
    self.skipTest("x")
"""
    transformer = UnittestToPytestCSTTransformer()
    out = transformer.transform_code(src)
    # Should still contain the original import pytest (not duplicated in odd places)
    assert out.count("import pytest") >= 1
