from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer


def run_transform(code: str) -> str:
    t = UnittestToPytestCstTransformer()
    return t.transform_code(code)


def test_support_id_call_preserved():
    code = """
import unittest

class T(unittest.TestCase):
    def test_a(self):
        x = self.id()
        assert x is not None
"""
    out = run_transform(code)
    # transform should complete and the id() call should remain or be syntactically valid
    assert "id()" in out


def test_support_shortDescription_call_preserved():
    code = """
import unittest

class T(unittest.TestCase):
    def test_b(self):
        sd = self.shortDescription()
        assert sd is None or sd
"""
    out = run_transform(code)
    assert "shortDescription()" in out
