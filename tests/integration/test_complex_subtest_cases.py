import ast
import pathlib
from collections.abc import Iterable

from splurge_unittest_to_pytest import main
from splurge_unittest_to_pytest.context import MigrationConfig
from tests.test_utils import (
    assert_class_structure,
    assert_code_structure_equals,
    assert_function_exists,
    assert_has_imports,
    assert_imports_equal,
)

DATA_DIR = pathlib.Path(__file__).resolve().parent / ".." / "data" / "given_and_expected_complex"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def _run_conversion_and_get_outputs(given: pathlib.Path) -> str:
    # Use the public migrate API to convert a file path with dry_run so we
    # can capture the generated code from the returned Result metadata.
    # The migration defaults now prefer parametrize-style pytest output,
    # so a dry-run override is sufficient.
    cfg = MigrationConfig().with_override(dry_run=True)

    res = main.migrate(str(given), cfg)
    # Expect metadata.generated_code mapping to exist and contain one entry
    meta = getattr(res, "metadata", None) or {}
    gen_map = meta.get("generated_code", {}) if isinstance(meta, dict) else {}
    if gen_map:
        # return the first generated value
        return next(iter(gen_map.values()))

    # Fallback: if no generated code was provided, attempt to read the
    # source file (should not happen in dry_run) and return it.
    return given.read_text(encoding="utf-8")


def _case_pairs() -> Iterable[tuple[pathlib.Path, pathlib.Path]]:
    base = DATA_DIR
    pairs = [
        (base / "unittest_given_51.txt", base / "pytest_expected_51.txt"),
        (base / "unittest_given_52.txt", base / "pytest_expected_52.txt"),
        (base / "unittest_given_53.txt", base / "pytest_expected_53.txt"),
    ]
    yield from pairs


def test_complex_given_expected_pairs_structure_and_imports():
    """Convert complex unittest files with subTest and verify structure + imports match expected pytest output."""
    for given, expected in _case_pairs():
        converted = _run_conversion_and_get_outputs(given)
        expected_text = _read(expected)

        # Extract expected imports from the expected text using AST so we
        # can pass a list of import strings to the helper.
        try:
            tree = ast.parse(expected_text)
            expected_imports = [
                ast.unparse(stmt).strip() for stmt in tree.body if isinstance(stmt, ast.Import | ast.ImportFrom)
            ]
        except Exception:
            expected_imports = []

        # High-level checks provided by helpers: ensure expected imports
        # exist in the converted output. Allow extra imports the converter
        # may add during transformation (e.g., datetime).
        if expected_imports:
            assert_has_imports(converted, expected_imports)
        else:
            # Fall back to ensuring key imports exist
            assert_has_imports(converted, ["import pytest"])

        # Enforce strict structural equality between the converted output
        # and the expected pytest file. An AssertionError here indicates the
        # converter failed to reproduce the complex subTest -> parametrize
        # behavior required by the test data and should be treated as a
        # regression rather than tolerated.
        assert_code_structure_equals(converted, expected_text)
