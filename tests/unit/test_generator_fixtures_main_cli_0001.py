import libcst as cst
from splurge_unittest_to_pytest.stages.generator import _is_literal
from splurge_unittest_to_pytest.stages.fixtures_stage import _update_test_function
from splurge_unittest_to_pytest.main import PatternConfigurator
from splurge_unittest_to_pytest import cli


def test_is_literal_simple():
    assert _is_literal(cst.Integer("1"))
    assert _is_literal(cst.SimpleString('"x"'))
    assert not _is_literal(cst.Call(func=cst.Name("make"), args=[]))


def test_update_test_function_adds_and_removes_params():
    fn = cst.FunctionDef(
        name=cst.Name("test_something"),
        params=cst.Parameters(params=[cst.Param(name=cst.Name("self"))]),
        body=cst.IndentedBlock(body=[]),
    )
    # remove_first True should drop self and add fixtures
    new = _update_test_function(fn, ["f1", "f2"], remove_first=True)
    names = [p.name.value for p in new.params.params]
    assert "self" not in names
    assert "f1" in names and "f2" in names


def test_pattern_configurator_basic():
    pc = PatternConfigurator()
    pc.add_setup_pattern("mysetup")
    assert pc._is_setup_method("mysetup")


def test_cli_main_callable_exists():
    # ensure the click main function object exists and is callable
    assert hasattr(cli, "main")
    assert callable(cli.main)
