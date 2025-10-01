from splurge_unittest_to_pytest.transformers import import_transformer


def test_add_pytest_imports_inserts_import():
    src = """
def foo():
    pass
"""
    out = import_transformer.add_pytest_imports(src)
    assert "import pytest" in out


def test_add_pytest_imports_preserves_existing():
    src = """
import pytest

def foo():
    return 1
"""
    out = import_transformer.add_pytest_imports(src)
    # Should not duplicate or remove existing import
    assert out.count("import pytest") == 1


def test_remove_unittest_imports_if_unused_removes_top_level():
    src = """
import unittest

def helper():
    return 1
"""
    out = import_transformer.remove_unittest_imports_if_unused(src)
    assert "import unittest" not in out


def test_remove_unittest_imports_if_used_keeps_import():
    src = """
import unittest

unittest.do_something()
"""
    out = import_transformer.remove_unittest_imports_if_unused(src)
    assert "import unittest" in out


def test_add_pytest_imports_inserts_re_with_alias_when_requested():
    src = """
def foo():
    __import__('pytest')
    pass
"""

    class T:
        needs_re_import = True
        re_alias = "re2"

    out = import_transformer.add_pytest_imports(src, transformer=T())
    # Dynamic detection may treat pytest as present (so no explicit import)
    # but the re alias should be inserted when requested
    assert "import re as re2" in out
