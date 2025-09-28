import libcst as cst

from splurge_unittest_to_pytest.transformers import import_transformer as it
from splurge_unittest_to_pytest.transformers import transformer_helper as th


def test_add_pytest_imports_inserts_when_missing():
    src = """
def foo():
    pass
"""
    out = it.add_pytest_imports(src)
    assert "import pytest" in out


def test_add_pytest_imports_respects_existing():
    src = "import pytest\n\nprint(1)\n"
    out = it.add_pytest_imports(src)
    assert out.count("import pytest") == 1


def test_remove_unittest_imports_if_unused_removes():
    src = "import unittest\n\nprint(1)\n"
    out = it.remove_unittest_imports_if_unused(src)
    assert "import unittest" not in out


def test_remove_unittest_imports_if_used_keeps():
    src = "import unittest\nprint(unittest)\n"
    out = it.remove_unittest_imports_if_unused(src)
    assert "import unittest" in out


def test_replacement_registry_and_applier(tmp_path):
    reg = th.ReplacementRegistry()

    # manually create a fake position-like object with start/end attributes
    class P:
        def __init__(self):
            self.start = type("S", (), {"line": 1, "column": 0})
            self.end = type("E", (), {"line": 1, "column": 10})

    p = P()
    repl = cst.Assert(test=cst.Name("True"))
    reg.record(p, repl)
    assert reg.get(p) is repl

    # apply via ReplacementApplier on a small module
    mod = cst.parse_module("foo(1)\n")
    applier = th.ReplacementApplier(reg)
    wrapper = cst.MetadataWrapper(mod)
    transformed = wrapper.visit(applier)
    # should not crash and returns a CST module
    assert transformed is not None


def test_add_pytest_imports_detects_dynamic_import_calls():
    src = "__import__('pytest')\nprint(1)\n"
    out = it.add_pytest_imports(src)
    # dynamic import should be treated as present; no duplicate import added
    assert out.count("import pytest") == 0


def test_add_re_import_when_transformer_requests():
    class T:
        needs_re_import = True
        re_alias = None
        re_search_name = None

    src = "def foo():\n    pass\n"
    out = it.add_pytest_imports(src, transformer=T())
    assert "import re" in out
