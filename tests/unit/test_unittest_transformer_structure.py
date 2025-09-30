"""Unit tests for helper utilities inside `UnittestToPytestCstTransformer`."""

from __future__ import annotations

import libcst as cst
import pytest
from libcst.metadata import MetadataWrapper, PositionProvider

from splurge_unittest_to_pytest.transformers.unittest_transformer import (
    UnittestToPytestCstTransformer,
)


def _first_node(source: str) -> cst.CSTNode:
    """Parse the source and return the first body node."""

    module = cst.parse_module(source)
    return module.body[0]


def _first_function(source: str) -> cst.FunctionDef:
    """Parse the source and return the first function definition."""

    module = cst.parse_module(source)
    for node in module.body:
        if isinstance(node, cst.FunctionDef):
            return node
    raise AssertionError("No function definition found in provided source")


def _render_statement(stmt: cst.CSTNode) -> str:
    """Render a statement node back to source code for comparison."""

    return cst.Module(body=[stmt]).code.strip()


def test_compute_module_insert_index_after_docstring_and_imports() -> None:
    transformer = UnittestToPytestCstTransformer()
    module = cst.parse_module('"""Module docs"""\nimport os\nfrom math import sqrt\n\nclass Sample:\n    pass\n')

    insert_index = transformer._compute_module_insert_index(module.body)

    assert insert_index == 3


@pytest.mark.parametrize(
    "source,expected",
    [
        ("def setUp():\n    pass\n", True),
        ("def helper():\n    pass\n", False),
        ("unittest.main()\n", True),
        ("pytest.main()\n", True),
    ],
)
def test_should_drop_top_level_node_for_lifecycle_and_main_calls(source: str, expected: bool) -> None:
    transformer = UnittestToPytestCstTransformer()
    node = _first_node(source)

    assert transformer._should_drop_top_level_node(node) is expected


def test_should_drop_top_level_node_for_main_guard() -> None:
    transformer = UnittestToPytestCstTransformer()
    node = _first_node("if __name__ == '__main__':\n    unittest.main()\n")

    assert transformer._should_drop_top_level_node(node) is True


def test_collect_module_fixtures_generates_expected_nodes() -> None:
    transformer = UnittestToPytestCstTransformer()
    transformer.setup_class_code = ["cls.level = True"]
    transformer.teardown_class_code = ["cls.level = False"]
    transformer.setup_code = ["self.value = 1"]
    transformer.teardown_code = ["self.value = 0"]
    transformer.setup_module_code = ["value = 'init'"]
    transformer.teardown_module_code = ["value = 'done'"]

    fixtures = transformer._collect_module_fixtures()

    assert {fixture.name.value for fixture in fixtures} == {
        "setup_class",
        "setup_method",
        "setup_module",
    }
    assert transformer.needs_pytest_import is True
    assert transformer.setup_class_code == []
    assert transformer.teardown_class_code == []
    assert transformer.setup_code == []
    assert transformer.teardown_code == []
    assert transformer.setup_module_code == []
    assert transformer.teardown_module_code == []


def test_setup_code_property_proxies_fixture_state() -> None:
    transformer = UnittestToPytestCstTransformer()

    transformer.setup_code.append("self.value = 1")

    assert transformer.fixture_state.instance_setup == ["self.value = 1"]

    transformer.fixture_state.instance_setup.append("self.other = 2")

    assert transformer.setup_code == ["self.value = 1", "self.other = 2"]


def test_visit_functiondef_populates_fixture_state() -> None:
    transformer = UnittestToPytestCstTransformer()
    function = _first_function("def setUp():\n    value = 1\n")

    transformer.visit_FunctionDef(function)
    try:
        assert transformer.fixture_state.instance_setup == ["value = 1"]
    finally:
        transformer.leave_FunctionDef(function, function)


def test_leave_module_clears_per_class_state_after_fixture_insertion() -> None:
    transformer = UnittestToPytestCstTransformer()
    transformer.fixture_state.per_class_setup["Sample"] = ["self.value = 1"]
    original = cst.parse_module("class Sample:\n    def test_case(self):\n        return True\n")

    updated = transformer.leave_Module(original, original)

    assert isinstance(updated, cst.Module)
    assert transformer.fixture_state.per_class_setup == {}


def test_rebuild_class_def_injects_fixtures_and_removes_lifecycle() -> None:
    transformer = UnittestToPytestCstTransformer()
    transformer._per_class_setup["Sample"] = ["self.value = 1"]
    transformer._per_class_teardown["Sample"] = ["self.value = 0"]
    class_node = _first_node(
        'class Sample:\n    """Docstring"""\n    def setUp(self):\n        pass\n    def test_case(self):\n        return True\n'
    )

    rebuilt = transformer._rebuild_class_def(class_node)

    assert isinstance(rebuilt.body, cst.IndentedBlock)
    statements = rebuilt.body.body
    assert isinstance(statements[0], cst.SimpleStatementLine)
    assert isinstance(statements[1], cst.FunctionDef)
    assert statements[1].name.value == "setup_method"
    assert all(not (isinstance(stmt, cst.FunctionDef) and stmt.name.value == "setUp") for stmt in statements)
    assert transformer.needs_pytest_import is True


def test_wrap_top_level_asserts_converts_non_class_statements() -> None:
    transformer = UnittestToPytestCstTransformer()
    module = cst.parse_module("class Example:\n    pass\n\nself.assertLogs('root')\n")

    wrapped = transformer._wrap_top_level_asserts(module.body)

    assert isinstance(wrapped[0], cst.ClassDef)
    assert any(isinstance(node, cst.With) for node in wrapped)


def test_rewrite_function_decorators_converts_unittest_skip() -> None:
    transformer = UnittestToPytestCstTransformer()
    function = _first_function("@unittest.skip('reason')\ndef sample():\n    pass\n")

    rewritten = transformer._rewrite_function_decorators(function)

    assert transformer.needs_pytest_import is True
    assert rewritten.decorators is not None
    decorator = rewritten.decorators[0].decorator
    assert isinstance(decorator, cst.Call)
    assert isinstance(decorator.func, cst.Attribute)
    assert isinstance(decorator.func.value, cst.Attribute)
    assert decorator.func.value.value.value == "pytest"
    assert decorator.func.attr.value == "skip"


def test_convert_simple_subtests_preserves_body_without_changes() -> None:
    transformer = UnittestToPytestCstTransformer()
    function = _first_function("def sample():\n    value = 1\n    return value\n")

    updated, body = transformer._convert_simple_subtests(function, function)

    assert updated == function
    assert [_render_statement(stmt) for stmt in body] == [_render_statement(stmt) for stmt in function.body.body]


def test_ensure_fixture_parameters_adds_request_when_needed() -> None:
    transformer = UnittestToPytestCstTransformer()
    transformer._functions_need_request.add("target")
    function = _first_function("def target():\n    pass\n")

    updated = transformer._ensure_fixture_parameters("target", function, function.body.body)

    assert any(param.name.value == "request" for param in updated.params.params)


def test_apply_recursive_with_rewrites_noop_for_simple_function() -> None:
    transformer = UnittestToPytestCstTransformer()
    function = _first_function("def trivial():\n    return 1\n")

    rewritten = transformer._apply_recursive_with_rewrites(function)

    assert _render_statement(rewritten) == _render_statement(function)


def test_parse_to_module_returns_module() -> None:
    transformer = UnittestToPytestCstTransformer()

    module = transformer._parse_to_module("def sample():\n    return 1\n")

    assert isinstance(module, cst.Module)
    assert module.code.strip().startswith("def sample")


def test_visit_with_metadata_marks_pytest_needed() -> None:
    transformer = UnittestToPytestCstTransformer()
    module = transformer._parse_to_module("@unittest.skip('later')\ndef sample():\n    pass\n")

    transformed = transformer._visit_with_metadata(module)

    assert isinstance(transformed, cst.Module)
    assert transformer.needs_pytest_import is True


def test_apply_recorded_replacements_applies_assertion_rewrite() -> None:
    transformer = UnittestToPytestCstTransformer()
    raw_module = transformer._parse_to_module("self.assertTrue(flag)\n")

    wrapper = MetadataWrapper(raw_module)
    module = wrapper.module
    metadata = wrapper.resolve(PositionProvider)
    stmt = module.body[0]
    assert isinstance(stmt, cst.SimpleStatementLine)
    expr = stmt.body[0]
    assert isinstance(expr, cst.Expr)
    call = expr.value
    assert isinstance(call, cst.Call)

    transformer.replacement_registry.record(
        metadata[call],
        cst.SimpleStatementLine(
            body=[
                cst.Assert(
                    test=cst.Name(value="flag"),
                )
            ]
        ),
    )

    updated = transformer._apply_recorded_replacements(module)

    new_stmt = updated.body[0]
    assert isinstance(new_stmt, cst.SimpleStatementLine)
    assert isinstance(new_stmt.body[0], cst.Assert)


def test_apply_recursive_with_cleanup_invokes_function_helpers() -> None:
    class RecordingTransformer(UnittestToPytestCstTransformer):
        def __init__(self) -> None:
            super().__init__()
            self.calls: list[str] = []

        def _apply_recursive_with_rewrites(self, node: cst.FunctionDef) -> cst.FunctionDef:
            self.calls.append(node.name.value)
            return node

    transformer = RecordingTransformer()
    module = transformer._parse_to_module(
        "def outer():\n    pass\n\nclass Inner:\n    def inside(self):\n        pass\n"
    )

    updated = transformer._apply_recursive_with_cleanup(module)

    assert isinstance(updated, cst.Module)
    assert transformer.calls == ["outer", "inside"]


def test_finalize_transformed_code_rewrites_assert_raises_and_imports() -> None:
    transformer = UnittestToPytestCstTransformer()
    transformer.needs_pytest_import = True

    result = transformer._finalize_transformed_code(
        "import unittest\n\nwith self.assertRaises(ValueError):\n    pass\n"
    )

    assert "pytest.raises" in result
    assert "import pytest" in result
    assert "import unittest" not in result


def test_run_inheritance_cleanup_removes_unittest_testcase_base() -> None:
    transformer = UnittestToPytestCstTransformer()
    module = transformer._parse_to_module(
        "import unittest\n\nclass Sample(unittest.TestCase, AnotherBase):\n    pass\n"
    )

    cleaned = transformer._run_inheritance_cleanup(module, {"Sample"})

    class_node = next(node for node in cleaned.body if isinstance(node, cst.ClassDef) and node.name.value == "Sample")

    assert len(class_node.bases) == 1
    base = class_node.bases[0]
    assert isinstance(base.value, cst.Name)
    assert base.value.value == "AnotherBase"


def test_run_inheritance_cleanup_normalizes_test_method_names() -> None:
    transformer = UnittestToPytestCstTransformer()
    module = transformer._parse_to_module(
        "import unittest\n\nclass Solo(unittest.TestCase):\n    def testExample(self):\n        pass\n"
    )

    cleaned = transformer._run_inheritance_cleanup(module, {"Solo"})

    class_node = next(node for node in cleaned.body if isinstance(node, cst.ClassDef) and node.name.value == "Solo")

    assert len(class_node.bases) == 0
    method = next(stmt for stmt in class_node.body.body if isinstance(stmt, cst.FunctionDef))
    assert method.name.value == "test_Example"
    assert "class Solo:" in cleaned.code
