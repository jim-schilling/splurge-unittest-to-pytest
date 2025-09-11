from pathlib import Path
import importlib.util
import sys

import pytest

from splurge_unittest_to_pytest.main import convert_string


def _import_from_path(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError("could not create spec")
    module = importlib.util.module_from_spec(spec)
    original = sys.modules.get(module_name)
    try:
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    finally:
        if original is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = original


def test_convert_and_import_all_data_files(tmp_path: Path) -> None:
    data_dir = Path(__file__).parents[2] / "tests" / "data"
    out_dir = tmp_path / "converted"
    out_dir.mkdir(parents=True, exist_ok=True)

    for p in sorted(data_dir.glob("unittest_*.txt")):
        src = p.read_text(encoding="utf8")
        res = convert_string(src, engine="pipeline", compat=True)
        code = getattr(res, "converted_code", None)
        assert code is not None, f"Conversion failed for {p}"

        out_file = out_dir / (p.stem + ".py")
        out_file.write_text(code, encoding="utf8")

        module_name = f"converted_{p.stem}"
        try:
            _import_from_path(module_name, out_file)
        except ModuleNotFoundError:
            # ignore missing third-party dependencies
            continue
        except NameError:
            # Do not swallow NameError: let it fail the test so missing
            # `import unittest` in converted output is detected.
            raise
        except Exception as exc:  # pragma: no cover - will surface real errors
            pytest.fail(f"Import failed for {p}: {exc!r}")
