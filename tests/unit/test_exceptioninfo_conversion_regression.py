from splurge_unittest_to_pytest.main import convert_string


def test_assertraises_conversion_uses_excinfo_value_end_to_end():
    src = """
import unittest

class T(unittest.TestCase):
    def test_it(self):
        with self.assertRaises(ValueError) as cm:
            raise ValueError('msg')
        # access
        e = cm.exception
"""

    result = convert_string(src)
    assert result.has_changes
    out = result.converted_code
    # final emitted code should use pytest.raises and access the ExceptionInfo via .value
    assert "with pytest.raises(ValueError) as cm:" in out
    assert "cm.value" in out
