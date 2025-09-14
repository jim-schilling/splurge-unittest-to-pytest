import libcst as cst
from splurge_unittest_to_pytest.stages.fixture_injector import fixture_injector_stage


def _make_module_with_placeholders() -> cst.Module:
    # simple module with an import so insertion happens after imports
    imp = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("os"))])])
    return cst.Module(body=[imp])


def _make_fn(name: str) -> cst.FunctionDef:
    return cst.FunctionDef(name=cst.Name(name), params=cst.Parameters(), body=cst.IndentedBlock(body=[cst.Pass()]))


def test_no_compat_inserts_two_blank_lines_before_defs() -> None:
    mod = _make_module_with_placeholders()
    nodes = [_make_fn("fix1"), _make_fn("fix2")]
    ctx = {"module": mod, "fixture_nodes": nodes}
    out = fixture_injector_stage(ctx)
    new_mod = out.get("module")
    assert isinstance(new_mod, cst.Module)
    # After insertion and normalization we expect two EmptyLine nodes before each top-level def.
    # Scan module.body and count EmptyLine runs preceding FunctionDef nodes.
    body = list(new_mod.body)
    positions = [i for i, n in enumerate(body) if isinstance(n, cst.FunctionDef)]
    assert positions, "No FunctionDef found"
    for pos in positions:
        # Count preceding empties
        cnt = 0
        j = pos - 1
        while j >= 0 and isinstance(body[j], cst.EmptyLine):
            cnt += 1
            j -= 1
        assert cnt >= 2, f"Expected >=2 EmptyLine before def at pos {pos}, found {cnt}"


def test_compat_preserves_single_empty_between_fixtures() -> None:
    mod = _make_module_with_placeholders()
    nodes = [_make_fn("a"), _make_fn("b")]
    ctx = {"module": mod, "fixture_nodes": nodes}
    out = fixture_injector_stage(ctx)
    new_mod = out.get("module")
    assert isinstance(new_mod, cst.Module)
    body = list(new_mod.body)
    # Compat mode removed; injector emits two EmptyLine before each top-level def.
    positions = [i for i, n in enumerate(body) if isinstance(n, cst.FunctionDef)]
    assert positions, "No FunctionDef found"
    for pos in positions:
        cnt = 0
        j = pos - 1
        while j >= 0 and isinstance(body[j], cst.EmptyLine):
            cnt += 1
            j -= 1
        assert cnt >= 2, f"Expected >=2 EmptyLine before def at pos {pos}, found {cnt}"
