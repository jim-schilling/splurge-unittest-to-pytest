import libcst as cst
from tests.unit.helpers.autouse_helpers import make_autouse_attach, insert_attach_fixture_into_module
import importlib
import inspect
import pkgutil
import types
import pytest
import subprocess
import sys
from pathlib import Path
from tools.rename_tests_by_domains import build_proposals


def test_build_attach_fixture_empty():
    func = make_autouse_attach({})
    assert isinstance(func, cst.FunctionDef)
    assert func.name.value == "_attach_to_instance"


def test_insert_attach_fixture_into_module():
    module = cst.parse_module("import pytest\n\n")
    func = make_autouse_attach(
        {"res": cst.FunctionDef(name=cst.Name("res"), params=cst.Parameters(), body=cst.IndentedBlock(body=[]))}
    )
    new_mod = insert_attach_fixture_into_module(module, func)
    assert any((isinstance(s, cst.FunctionDef) and s.name.value == "_attach_to_instance" for s in new_mod.body))


PACKAGE = "splurge_unittest_to_pytest"
SKIP_MODULES = {f"{PACKAGE}.print_diagnostics"}


def _safe_call(obj):
    """Call a callable if it has no required parameters.

    Returns True if called, False otherwise.
    """
    if not callable(obj):
        return False
    try:
        sig = inspect.signature(obj)
    except (ValueError, TypeError):
        return False
    for p in sig.parameters.values():
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            return False
        if p.default is inspect._empty and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY):
            return False
    try:
        obj()
        return True
    except Exception:
        return False


@pytest.mark.parametrize("module_name", list(pkgutil.iter_modules([PACKAGE.replace(".", "/")])))
def test_import_and_call_public_symbols(module_name):
    if isinstance(module_name, pkgutil.ModuleInfo):
        name = module_name.name
    else:
        name = module_name[1]
    full = f"{PACKAGE}.{name}"
    if full in SKIP_MODULES:
        pytest.skip(f"Skipping unsafe module {full}")
    mod = importlib.import_module(full)
    assert isinstance(mod, types.ModuleType)
    for attr_name in dir(mod):
        if attr_name.startswith("_"):
            continue
        try:
            attr = getattr(mod, attr_name)
        except Exception:
            pytest.fail(f"Accessing attribute {full}.{attr_name} raised")
        if inspect.ismodule(attr):
            continue
        _safe_call(attr)
    for subpkg in ("stages", "converter"):
        iter_path = f"{PACKAGE}/{subpkg}".replace(".", "/")
        for _info in pkgutil.iter_modules([iter_path]):
            name = _info.name if isinstance(_info, pkgutil.ModuleInfo) else _info[1]
            full = f"{PACKAGE}.{subpkg}.{name}"

            def _make_test(*, modname=full):
                def _test():
                    if modname in SKIP_MODULES:
                        pytest.skip(f"Skipping unsafe module {modname}")
                    mod = importlib.import_module(modname)
                    assert isinstance(mod, types.ModuleType)
                    for attr_name in dir(mod):
                        if attr_name.startswith("_"):
                            continue
                        try:
                            attr = getattr(mod, attr_name)
                        except Exception:
                            pytest.fail(f"Accessing attribute {modname}.{attr_name} raised")
                        _safe_call(attr)

                return _test

            globals()[f"test_smoke_{subpkg}_{name}"] = _make_test(modname=full)


def test_print_diagnostics_finds_run(tmp_path: Path) -> None:
    root = tmp_path / "diag_root"
    root.mkdir()
    run_dir = root / "splurge-diagnostics-2025-09-12_12-00-00"
    run_dir.mkdir()
    marker = run_dir / "splurge-diagnostics-2025-09-12_12-00-00"
    marker.write_text(str(run_dir.resolve()), encoding="utf-8")
    sample = run_dir / "test_snapshot.py"
    sample.write_text("x = 1", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "tools/print_diagnostics.py", "--root", str(root)], capture_output=True, text=True, check=False
    )
    out = proc.stdout + proc.stderr
    assert "Diagnostics run directory" in out
    assert "splurge-diagnostics-2025-09-12_12-00-00" in out
    assert "test_snapshot.py" in out


def test_renamer_skips_helpers_and_non_test_files(tmp_path: Path) -> None:
    root = tmp_path / "tests"
    helpers = root / "unit" / "helpers"
    helpers.mkdir(parents=True)
    tests_dir = root / "unit"
    h = helpers / "autouse_helpers.py"
    # helper modules should not be considered by the renamer, but the
    # test expects that helper files can contain DOMAINS metadata in real
    # repos; here we simulate a helper with core domain so the renamer
    # logic can be validated against nearby test files.
    h.write_text("DOMAINS = ['core']\n")
    conf = tests_dir / "conftest.py"
    conf.write_text("DOMAINS = ['misc']\n")
    real = tests_dir / "test_example.py"
    real.write_text("DOMAINS = ['core']\n")
    proposals = build_proposals(root)
    names = [p.name for _, p in proposals]
    assert any(("test_core" in n for n in names))
    assert not any(("autouse_helpers" in n for n in names))
    assert not any(("conftest" in n for n in names))
