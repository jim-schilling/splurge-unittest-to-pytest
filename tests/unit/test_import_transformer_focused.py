import libcst as cst

from splurge_unittest_to_pytest.transformers import import_transformer as it


def test_add_pytest_imports_inserts_pytest_and_re_alias():
    src = """import os
from something import x
"""

    class Dummy:
        needs_re_import = True
        re_alias = "re2"

    out = it.add_pytest_imports(src, transformer=Dummy())
    assert "import pytest" in out
    assert "import re as re2" in out or "import re2" in out


def test_add_pytest_imports_detects_dynamic_import():
    src = """# dynamic import
__import__('pytest')
"""
    out = it.add_pytest_imports(src, transformer=None)
    # dynamic import should be treated as evidence; function should not inject an explicit top-level import
    assert "__import__('pytest')" in out
    assert "import pytest" not in out


def test_remove_unittest_imports_if_unused_removes():
    src = """import unittest
def f():
    return 1
"""
    out = it.remove_unittest_imports_if_unused(src)
    assert "import unittest" not in out
