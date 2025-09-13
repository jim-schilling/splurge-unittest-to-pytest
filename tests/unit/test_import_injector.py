import libcst as cst
from typing import cast
from splurge_unittest_to_pytest.stages.import_injector import import_injector_stage


def test_import_injector_inserts_after_docstring() -> None:
    src = '"""module doc"""\n\nclass A:\n    pass\n'
    module = cst.parse_module(src)
    ctx: dict[str, object] = {"module": module}
    res = import_injector_stage(ctx)
    new_module = cast(cst.Module, res.get("module"))
    # first stmt should remain docstring, second should be import
    assert isinstance(new_module.body[0], cst.SimpleStatementLine)
    assert isinstance(new_module.body[1], cst.SimpleStatementLine)
    # the import should contain pytest
    import_stmt = new_module.body[1].body[0]
    assert isinstance(import_stmt, cst.Import)
    assert import_stmt.names[0].name.value == "pytest"


def test_import_injector_no_duplicate() -> None:
    src = "import pytest\n\nclass A:\n    pass\n"
    module = cst.parse_module(src)
    ctx: dict[str, object] = {"module": module}
    res = import_injector_stage(ctx)
    new_module = cast(cst.Module, res.get("module"))
    # ensure still only one import pytest (first stmt)
    imports = [s.body[0] for s in new_module.body if isinstance(s, cst.SimpleStatementLine) and s.body]
    pytest_imports = [i for i in imports if isinstance(i, cst.Import) and i.names[0].name.value == "pytest"]
    assert len(pytest_imports) == 1
