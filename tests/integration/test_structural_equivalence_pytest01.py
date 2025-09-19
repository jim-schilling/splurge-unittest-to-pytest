import libcst as cst
from pathlib import Path

from splurge_unittest_to_pytest.main import convert_string


def _find_test_def(mod: cst.Module, name: str = "test_something") -> cst.FunctionDef | None:
    for stmt in mod.body:
        if isinstance(stmt, cst.FunctionDef) and stmt.name.value == name:
            return stmt
    return None


def _has_pytest_fixture(mod: cst.Module) -> bool:
    for stmt in mod.body:
        if isinstance(stmt, cst.FunctionDef):
            for dec in stmt.decorators:
                d = dec.decorator
                # match @pytest.fixture
                if isinstance(d, cst.Attribute) and isinstance(d.value, cst.Name) and d.value.value == "pytest":
                    if isinstance(d.attr, cst.Name) and d.attr.value == "fixture":
                        return True
    return False


def _load_module_from_text(text: str) -> cst.Module:
    return cst.parse_module(text)


def _assert_structural_equivalent(converted_code: str, golden_code: str) -> None:
    converted = _load_module_from_text(converted_code)
    golden = _load_module_from_text(golden_code)

    # golden must have a pytest fixture
    assert _has_pytest_fixture(golden), "golden file must include a pytest fixture"

    # converted must either include a pytest fixture or its test function must accept a single parameter
    if _has_pytest_fixture(converted):
        return

    test_def = _find_test_def(converted)
    assert test_def is not None, "converted output must contain test_something"
    # require exactly one parameter for dependency injection
    assert len(test_def.params.params) == 1, "converted test function must accept a single fixture parameter"


def test_a_produces_structural_equivalent():
    src = Path("tests/data/unittest_pytest_samples/unittest_01_a.py.txt").read_text()
    golden = Path("tests/data/unittest_pytest_samples/pytest_01.py.txt").read_text()
    res = convert_string(src, normalize_names=False)
    assert res.errors == []
    assert res.has_changes
    _assert_structural_equivalent(res.converted_code, golden)


def test_b_produces_structural_equivalent():
    src = Path("tests/data/unittest_pytest_samples/unittest_01_b.py.txt").read_text()
    golden = Path("tests/data/unittest_pytest_samples/pytest_01.py.txt").read_text()
    res = convert_string(src, normalize_names=False)
    assert res.errors == []
    assert res.has_changes
    _assert_structural_equivalent(res.converted_code, golden)
