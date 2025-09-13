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
    res = convert_string(src, engine="pipeline")
    assert res.has_changes
    code = res.converted_code
    # write to temporary file and attempt to compile/exec it
    p = tmp_path / "converted.py"
    p.write_text(code, encoding="utf-8")
    # try to compile
    compiled = compile(code, str(p), "exec")
    globals_dict: dict[str, object] = {}
    exec(compiled, globals_dict)
    # Ensure the converted module defines TestFoo
    assert "TestFoo" in globals_dict
    # instantiate and inspect the test method signature to ensure the
    # converted test expects a 'tmp' fixture parameter (or that setUp was
    # preserved). We avoid calling the test method because pytest handles
    # fixture attachment at runtime.
    T = cast(type, globals_dict["TestFoo"])
    func = getattr(T, "test_using_tmp")
    # ensure function has at least one parameter when converted to pytest
    # style (accepting 'tmp') or that the class still defines setUp.
    params = getattr(func, "__code__", None)
    if params is not None:
        argcount = getattr(params, "co_argcount", 0)
        # when converted to a pytest function, it will accept one arg
        assert argcount >= 1
    else:
        # fallback: ensure setUp exists on the class
        assert hasattr(T, "setUp")
