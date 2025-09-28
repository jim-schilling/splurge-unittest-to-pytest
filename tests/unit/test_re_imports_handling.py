import textwrap

from splurge_unittest_to_pytest.transformers.unittest_transformer import (
    UnittestToPytestCstTransformer,
)


def transform(code: str) -> str:
    return UnittestToPytestCstTransformer().transform_code(textwrap.dedent(code))


def test_from_re_import_search_uses_search_and_no_import_added():
    code = """
from re import search
import unittest

class T(unittest.TestCase):
    def test_regex(self):
        self.assertRegex("abc", "a.")
"""
    out = transform(code)
    # should use search(...) form and not add an import re
    assert "search(" in out
    assert "import re" not in out


def test_import_re_as_alias_uses_alias_search():
    code = """
import re as r
import unittest

class T(unittest.TestCase):
    def test_regex(self):
        self.assertRegex("abc", "a.")
"""
    out = transform(code)
    # should use r.search(...) and keep the alias import
    assert "r.search(" in out
    assert "import re as r" in out


def test_no_re_import_adds_import_and_uses_re_search():
    code = """
import unittest

class T(unittest.TestCase):
    def test_regex(self):
        self.assertRegex("abc", "a.")
"""
    out = transform(code)
    # should add import re and use re.search(...)
    assert "import re" in out
    assert "re.search(" in out
