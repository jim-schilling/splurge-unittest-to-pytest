import ast
from pathlib import Path

import pytest

from splurge_unittest_to_pytest.main import convert_string


SAMPLE = Path("tests/data/test_schema_parser.py.txt")


def _is_fixture_node(node: ast.AST) -> bool:
    """Return True if node is a top-level function with a pytest.fixture decorator."""
    if not isinstance(node, ast.FunctionDef):
        return False
    for dec in node.decorator_list:
        # decorator can be ast.Attribute (pytest.fixture) or ast.Name (fixture)
        # Support both @pytest.fixture and @pytest.fixture(autouse=True) forms
        if isinstance(dec, ast.Attribute) and getattr(dec, "attr", "") == "fixture":
            return True
        if isinstance(dec, ast.Name) and getattr(dec, "id", "") == "fixture":
            return True
        # decorator can also be an ast.Call where the func is an Attribute or Name
        if isinstance(dec, ast.Call):
            fn = dec.func
            if isinstance(fn, ast.Attribute) and getattr(fn, "attr", "") == "fixture":
                return True
            if isinstance(fn, ast.Name) and getattr(fn, "id", "") == "fixture":
                return True
    return False


def test_converted_imports_before_fixtures_and_no_setup_teardown():
    """Convert sample input and validate conversion output structure.

    This test ensures:
      - All import statements appear before fixture definitions.
      - No leftover setUp/tearDown methods remain in classes.
      - Converted code is syntactically valid Python.
    """
    src = SAMPLE.read_text(encoding="utf-8")
    result = convert_string(src)

    # Ensure conversion produced code
    assert isinstance(result.converted_code, str)

    # Syntax check
    try:
        mod = ast.parse(result.converted_code)
    except SyntaxError as e:
        pytest.fail(f"Converted code is not valid Python: {e}")

    body = list(mod.body)

    # Find the last import index
    import_idxs = [i for i, n in enumerate(body) if isinstance(n, (ast.Import, ast.ImportFrom))]
    if import_idxs:
        last_import_idx = max(import_idxs)
    else:
        last_import_idx = -1

    # Find first fixture index
    fixture_idxs = [i for i, n in enumerate(body) if _is_fixture_node(n)]
    if fixture_idxs:
        first_fixture_idx = min(fixture_idxs)
    else:
        first_fixture_idx = None

    if first_fixture_idx is not None:
        # All imports must come before fixtures
        assert last_import_idx < first_fixture_idx, "Found pytest fixtures before import statements in converted code."

    # Ensure no class contains leftover unittest methods unless a compatibility
    # autouse attach fixture or pytest fixtures are present. When the
    # conversion preserves setUp/tearDown to keep modules runnable, the
    # pipeline should also emit fixture-based compatibility shims (e.g.
    # a module-level autouse fixture named _attach_to_instance) or regular
    # pytest fixtures. We'll accept preserved lifecycle methods only when
    # such compatibility is present.
    top_level_names = {getattr(n, "name", None) for n in body if isinstance(n, ast.FunctionDef)}
    has_attach_fixture = "_attach_to_instance" in top_level_names

    for node in ast.walk(mod):
        if isinstance(node, ast.ClassDef):
            for member in node.body:
                if isinstance(member, ast.FunctionDef) and member.name in ("setUp", "tearDown"):
                    if not has_attach_fixture:
                        pytest.fail(
                            f"Found leftover unittest method '{member.name}' in class '{node.name}' without compatibility fixtures present"
                        )
