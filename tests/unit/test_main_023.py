from splurge_unittest_to_pytest.main import convert_string

DOMAINS = ["main"]


def _convert_and_code(src: str) -> str:
    res = convert_string(src)
    return res.converted_code


def test_removes_simple_unittest_main_guard():
    src = """
import unittest

if __name__ == '__main__':
    unittest.main()
"""
    code = _convert_and_code(src)
    assert "unittest.main" not in code
    assert "if __name__" not in code


def test_removes_sys_exit_wrapped_main():
    src = """
import unittest
import sys

if __name__ == "__main__":
    sys.exit(unittest.main())
"""
    code = _convert_and_code(src)
    assert "unittest.main" not in code
    assert "sys.exit" not in code or "__main__" not in code


def test_handles_double_quoted_main_guard_with_name_call():
    src = '"""module"""\nif __name__ == "__main__":\n    main()\n'
    code = _convert_and_code(src)
    # If main() is standalone we remove the guard only if it matches our pattern
    assert "if __name__" not in code
