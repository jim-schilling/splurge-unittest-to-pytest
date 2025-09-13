import libcst as cst

from splurge_unittest_to_pytest.converter import fixtures


def test_create_simple_fixture_structure_and_decorator():
    fd = fixtures.create_simple_fixture("my_fixture", cst.parse_expression("42"))
    code = cst.Module(body=[fd]).code
    # basic shape
    assert isinstance(fd, cst.FunctionDef)
    assert fd.name.value == "my_fixture"
    # should either assign to a local and return it, or return the literal directly
    if "_my_fixture_value" in code:
        assert "return _my_fixture_value" in code
    else:
        assert "return 42" in code
    # decorator should reference pytest.fixture
    assert "pytest.fixture" in code


def test_create_fixture_with_cleanup_replaces_names_and_yields():
    cleanup_stmt = cst.parse_statement("cleanup(self.x)")
    fd = fixtures.create_fixture_with_cleanup("x", cst.parse_expression("1"), [cleanup_stmt])
    code = cst.Module(body=[fd]).code
    assert isinstance(fd, cst.FunctionDef)
    # yield should appear for cleanup fixtures
    assert "yield _x_value" in code
    # cleanup statements should reference the local _x_value (not self.x)
    assert "_x_value" in code and "self.x" not in code


def test_make_autouse_attach_to_instance_fixture_builds_setters():
    # use create_simple_fixture to produce a FunctionDef value for the mapping
    foo_fd = fixtures.create_simple_fixture("foo", cst.parse_expression("1"))
    module_fn = fixtures.make_autouse_attach_to_instance_fixture({"foo": foo_fd})
    code = cst.Module(body=[module_fn]).code
    assert isinstance(module_fn, cst.FunctionDef)
    # function name and common helper calls
    assert module_fn.name.value == "_attach_to_instance"
    assert "getattr" in code
    assert "setattr" in code
    # autouse should be present in decorator args (accept spacing variations)
    assert "autouse" in code and "True" in code


def test_add_autouse_attach_fixture_to_module_inserts_after_pytest_import():
    mod = cst.parse_module("import pytest\n")
    foo_fd = fixtures.create_simple_fixture("bar", cst.parse_expression("2"))
    new_mod = fixtures.add_autouse_attach_fixture_to_module(mod, {"bar": foo_fd})
    code = new_mod.code
    # import should come before the inserted fixture
    assert "import pytest" in code
    assert "_attach_to_instance" in code
    assert code.find("import pytest") < code.find("_attach_to_instance")


def test_create_fixture_for_attribute_dispatches_to_cleanup_or_simple():
    # when teardown_cleanup has an entry, fixture with yield is produced
    td = {"a": [cst.parse_statement("cleanup(self.a)")]}
    fd1 = fixtures.create_fixture_for_attribute("a", cst.parse_expression("0"), td)
    assert "yield _a_value" in cst.Module(body=[fd1]).code

    # when no cleanup, simple fixture (return) is produced
    fd2 = fixtures.create_fixture_for_attribute("b", cst.parse_expression("0"), {})
    code2 = cst.Module(body=[fd2]).code
    assert ("return _b_value" in code2) or ("return 0" in code2)
