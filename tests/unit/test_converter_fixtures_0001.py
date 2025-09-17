import libcst as cst

from splurge_unittest_to_pytest.converter.fixtures import (
    create_simple_fixture,
    create_fixture_with_cleanup,
    create_fixture_for_attribute,
)
from tests.unit.helpers.autouse_helpers import make_autouse_attach, insert_attach_fixture_into_module

DOMAINS = ["converter", "fixtures"]


# Use shared test helpers imported from tests.unit.helpers.autouse_helpers


def render_node(node: cst.CSTNode) -> str:
    # Helper to render a node inside a module for stable text assertions
    return cst.Module(
        body=[node] if isinstance(node, cst.BaseStatement) or isinstance(node, cst.FunctionDef) else [node]
    ).code


def test_create_simple_fixture_renders_return_and_decorator():
    func = create_simple_fixture("myattr", cst.parse_expression("'value'"))
    src = render_node(func)

    assert "@pytest.fixture" in src
    assert "def myattr()" in src
    # local value may be emitted as an assignment+return or as a direct return of the literal
    assert ("_myattr_value = 'value'" in src and "return _myattr_value" in src) or ("return 'value'" in src)


def test_create_fixture_with_cleanup_replaces_attribute_in_cleanup():
    # Make a fake cleanup call that references the attribute name
    cleanup_stmts = [
        cst.SimpleStatementLine(
            body=[cst.Expr(value=cst.Call(func=cst.Name("cleanup"), args=[cst.Arg(value=cst.Name("the_attr"))]))]
        )
    ]

    func = create_fixture_with_cleanup("the_attr", cst.parse_expression("1"), cleanup_stmts)
    src = render_node(func)

    # Should use yield pattern
    assert "yield _the_attr_value" in src
    # Assignment to local value must be present
    assert "_the_attr_value = 1" in src
    # cleanup call should reference the local name, not the original attribute
    assert "cleanup(_the_attr_value)" in src


def test_make_autouse_attach_to_instance_fixture_and_module_insertion():
    # Create minimal fixture functions to inject
    f1 = create_simple_fixture("a", cst.parse_expression("1"))
    f2 = create_simple_fixture("b", cst.parse_expression("2"))
    fixtures = {"a": f1, "b": f2}

    func = make_autouse_attach(fixtures)
    src = render_node(func)

    # autouse decorator should be present (allow spacing variations) and function name as expected
    assert "pytest.fixture" in src
    assert "autouse" in src
    assert "def _attach_to_instance(request)" in src
    # Should set both attributes on inst
    assert "setattr(inst, 'a', a)" in src
    assert "setattr(inst, 'b', b)" in src

    # Now test insertion into a module that already imports pytest
    module = cst.parse_module("import pytest\n\n# existing\n")

    new_module = insert_attach_fixture_into_module(module, make_autouse_attach(fixtures))
    code = new_module.code

    # The inserted autouse fixture should be present in the module
    assert "def _attach_to_instance(request)" in code


def test_create_fixture_for_attribute_delegation():
    # Attribute with cleanup should produce a yield fixture
    cleanup_for_a = {
        "a": [
            cst.SimpleStatementLine(
                body=[cst.Expr(value=cst.Call(func=cst.Name("do_cleanup"), args=[cst.Arg(value=cst.Name("a"))]))]
            )
        ]
    }

    f_a = create_fixture_for_attribute("a", cst.parse_expression("'x'"), cleanup_for_a)
    src_a = render_node(f_a)
    assert "yield _a_value" in src_a

    # Attribute without cleanup should produce a simple return fixture
    f_b = create_fixture_for_attribute("b", cst.parse_expression("'y'"), {})
    src_b = render_node(f_b)
    # may be emitted as direct return or assignment+return
    assert ("return _b_value" in src_b) or ("return 'y'" in src_b)
