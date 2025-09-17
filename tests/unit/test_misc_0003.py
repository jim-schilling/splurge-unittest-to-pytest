import importlib
import inspect
import pkgutil
import types

import pytest

DOMAINS = ["misc"]
PACKAGE = "splurge_unittest_to_pytest"

# Modules to skip because they intentionally perform side-effects or are
# heavyweight. Add to this list if a module causes the smoke test to fail.
SKIP_MODULES = {
    f"{PACKAGE}.print_diagnostics",
}


def _safe_call(obj):
    """Call a callable if it has no required parameters.

    Returns True if called, False otherwise.
    """
    if not callable(obj):
        return False
    try:
        sig = inspect.signature(obj)
    except (ValueError, TypeError):
        # Some C builtins may not expose a signature; skip them.
        return False
    # Only call callables with no required positional or keyword-only args.
    for p in sig.parameters.values():
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            # skip varargs/kwargs: we don't provide any
            return False
        if p.default is inspect._empty and p.kind in (
            p.POSITIONAL_ONLY,
            p.POSITIONAL_OR_KEYWORD,
            p.KEYWORD_ONLY,
        ):
            return False
    # If we reached here, attempt call without arguments
    try:
        obj()
        return True
    except Exception:
        # Swallow exceptions from calls — we only aim to exercise code paths,
        # not assert specific behavior. Tests should still fail for import-time
        # errors.
        return False


@pytest.mark.parametrize("module_name", list(pkgutil.iter_modules([PACKAGE.replace(".", "/")])))
def test_import_and_call_public_symbols(module_name):
    # param module_name is a ModuleInfo tuple-like; convert to full name
    if isinstance(module_name, pkgutil.ModuleInfo):
        name = module_name.name
    else:
        # Backwards compat: some pkgutil variants yield tuples
        name = module_name[1]
    full = f"{PACKAGE}.{name}"
    if full in SKIP_MODULES:
        pytest.skip(f"Skipping unsafe module {full}")
    # Import the module
    mod = importlib.import_module(full)
    assert isinstance(mod, types.ModuleType)
    # Iterate public attributes and call safe zero-arg callables
    for attr_name in dir(mod):
        if attr_name.startswith("_"):
            continue
        try:
            attr = getattr(mod, attr_name)
        except Exception:
            # attribute access raised; consider this a failure
            pytest.fail(f"Accessing attribute {full}.{attr_name} raised")
        # If it's a submodule, attempt to import it
        if inspect.ismodule(attr):
            continue
        _safe_call(attr)


# Also exercise subpackages 'stages' and 'converter' modules' top-level modules
for subpkg in ("stages", "converter"):
    iter_path = f"{PACKAGE}/{subpkg}".replace(".", "/")
    for _info in pkgutil.iter_modules([iter_path]):
        name = _info.name if isinstance(_info, pkgutil.ModuleInfo) else _info[1]
        full = f"{PACKAGE}.{subpkg}.{name}"

        def _make_test(modname=full):
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

        globals()[f"test_smoke_{subpkg}_{name}"] = _make_test()
