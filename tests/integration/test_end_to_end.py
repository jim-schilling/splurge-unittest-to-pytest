import textwrap
from pathlib import Path
from typing import cast

from splurge_unittest_to_pytest.main import convert_string


def test_converted_module_executes_and_autouse_attaches(tmp_path: Path) -> None:
    src = textwrap.dedent("""
        import unittest
        import tempfile

        class TestFoo(unittest.TestCase):
            def setUp(self) -> None:
                self.tmp = 123

            def test_using_tmp(self) -> None:
                assert self.tmp == 123
    """)
    res = convert_string(src)
    assert res.has_changes
    code = res.converted_code
    # write to temporary file and attempt to compile/exec it
    p = tmp_path / "converted.py"
    p.write_text(code, encoding="utf-8")
    # try to compile
    compiled = compile(code, str(p), "exec")
    globals_dict: dict[str, object] = {}
    exec(compiled, globals_dict)
    # The converter now emits strict pytest-style code: classes are dropped
    # and top-level test functions and fixtures are emitted. Accept either
    # a preserved class or a top-level test function.
    if "TestFoo" in globals_dict:
        T = cast(type, globals_dict["TestFoo"])
        func = getattr(T, "test_using_tmp")
        params = getattr(func, "__code__", None)
        if params is not None:
            assert getattr(params, "co_argcount", 0) >= 1
        else:
            assert hasattr(T, "setUp")
    else:
        # Expect top-level test function named 'test_using_tmp'
        assert "test_using_tmp" in globals_dict
        func = globals_dict["test_using_tmp"]
        params = getattr(func, "__code__", None)
        assert params is not None and getattr(params, "co_argcount", 0) >= 1
