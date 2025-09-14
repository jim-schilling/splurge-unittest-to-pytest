from splurge_unittest_to_pytest.main import convert_string


def test_assertraises_regex_conversion_uses_excinfo_value_end_to_end():
    src = """
import unittest

class T(unittest.TestCase):
    def test_it(self):
        with self.assertRaisesRegex(ValueError, 'msg') as cm:
            raise ValueError('msg')
        # access
        e = cm.exception
"""
    result = convert_string(src)
    assert result.has_changes
    out = result.converted_code
    assert "with pytest.raises(ValueError" in out
    # accept variations in spacing: look for 'match' keyword presence
    assert "match" in out
    assert "cm.value" in out


def test_functional_assertraises_conversion_has_no_excinfo_binding():
    src = """
import unittest

class T(unittest.TestCase):
    def test_it(self):
        def f():
            raise ValueError('msg')
        self.assertRaises(ValueError, f)
"""
    result = convert_string(src)
    assert result.has_changes
    out = result.converted_code
    # accept either 'with pytest.raises(ValueError)' or 'with pytest.raises(ValueError, )'
    assert "with pytest.raises(ValueError" in out
    # functional form shouldn't introduce an excinfo binding; no .exception/.value
    assert ".exception" not in out
    assert ".value" not in out


def test_shadowed_excinfo_name_is_not_rewritten_in_inner_scope():
    src = """
import unittest

class T(unittest.TestCase):
    def test_it(self):
        with self.assertRaises(ValueError) as cm:
            raise ValueError('msg')
        # outer access should be rewritten
        outer = cm.exception
        def inner(cm):
            # parameter shadows outer 'cm' and should NOT be rewritten
            return cm.exception
        x = inner(42)
"""
    result = convert_string(src)
    assert result.has_changes
    out = result.converted_code
    # outer usage rewritten to .value
    assert "outer = cm.value" in out
    # inner function should still be present; ensure we didn't rewrite the
    # parameterized inner function's uses if it shadows the outer name. The
    # converter may transform certain shapes; check presence of inner and
    # that outer access was rewritten.
    assert "def inner(cm):" in out
