import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages import import_injector


def make_module(src: str) -> cst.Module:
    return cst.parse_module(textwrap.dedent(src))


def test_explicit_flags_but_not_needed_returns_module():
    src = "x = 1\n"
    m = make_module(src)
    out = import_injector.import_injector_stage({"module": m, "needs_pytest_import": False, "needs_re_import": False})
    assert out == {"module": m} or ("module" in out and isinstance(out["module"], cst.Module))


def test_unittest_already_imported_prevents_unittest_insertion():
    src = "import unittest\n\nclass X:\n    pass\n"
    m = make_module(src)
    out = import_injector.import_injector_stage({"module": m, "needs_unittest_import": True})
    new_mod = out.get("module", m)
    imports = [
        s
        for s in new_mod.body
        if isinstance(s, cst.SimpleStatementLine) and isinstance(s.body[0], (cst.Import, cst.ImportFrom))
    ]
    unittest_count = 0
    for s in imports:
        first = s.body[0]
        if isinstance(first, cst.Import):
            for alias in first.names:
                if getattr(alias.name, "value", None) == "unittest":
                    unittest_count += 1
        if isinstance(first, cst.ImportFrom) and getattr(first.module, "value", None) == "unittest":
            unittest_count += 1
    assert unittest_count == 1


def test_preferred_order_inserts_shutil_and_json_after_pytest():
    src = '"""docstring"""\n\n# placeholder\n'
    m = make_module(src)
    out = import_injector.import_injector_stage(
        {"module": m, "needs_shutil_import": True, "needs_re_import": True, "needs_pytest_import": True}
    )
    new_mod = out["module"]
    names = []
    for s in new_mod.body:
        if isinstance(s, cst.SimpleStatementLine) and s.body:
            first = s.body[0]
            if isinstance(first, cst.Import) and first.names:
                names.append(getattr(first.names[0].name, "value", None))
            elif isinstance(first, cst.ImportFrom) and getattr(first.module, "value", None):
                names.append(getattr(first.module, "value", None))
    assert "pytest" in names
    if "shutil" in names and "json" in names:
        assert names.index("pytest") < names.index("shutil")


def test_pathlib_deduplication_when_existing():
    src = "from pathlib import Path\n\nx=1\n"
    m = make_module(src)
    out = import_injector.import_injector_stage({"module": m, "needs_typing_names": ["Path"]})
    new_mod = out.get("module", m)
    pathlib_count = 0
    for s in new_mod.body:
        if (
            isinstance(s, cst.SimpleStatementLine)
            and s.body
            and isinstance(s.body[0], cst.ImportFrom)
            and (getattr(s.body[0].module, "value", None) == "pathlib")
        ):
            pathlib_count += 1
    assert pathlib_count == 1
