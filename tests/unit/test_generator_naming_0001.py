import libcst as cst
from splurge_unittest_to_pytest.stages.generator_parts.filename_inferer import infer_filename_for_local
from splurge_unittest_to_pytest.stages.generator_parts.module_level_names import collect_module_level_names
from splurge_unittest_to_pytest.stages.generator_parts.name_allocator import choose_local_name


class Dummy:
    def __init__(self, local_map):
        self.local_assignments = local_map


def test_infer_from_simple_call():
    call = cst.parse_expression("helper('path/to/file.txt')")
    d = Dummy({"_x_value": (call, None)})
    assert infer_filename_for_local("_x_value", d) == "path/to/file.txt"


def test_no_entry_returns_none():
    d = Dummy({})
    assert infer_filename_for_local("missing", d) is None


def test_non_call_assignment_returns_none():
    d = Dummy({"_x_value": (cst.Name("x"), None)})
    assert infer_filename_for_local("_x_value", d) is None


def test_call_without_string_returns_none():
    call = cst.parse_expression("helper(123)")
    d = Dummy({"_x_value": (call, None)})
    assert infer_filename_for_local("_x_value", d) is None


def test_collect_module_level_names_assign_and_defs():
    mod = cst.parse_module("\n".join(["X = 1", "def foo():\n    pass", "class Bar:\n    pass"]))
    names = collect_module_level_names(mod)
    assert "X" in names
    assert "foo" in names
    assert "Bar" in names


def test_collect_module_level_names_imports_and_aliases():
    mod = cst.parse_module("\n".join(["import os", "import sys as system", "from math import sqrt, pi as PI"]))
    names = collect_module_level_names(mod)
    assert "os" in names
    assert "system" in names
    assert "sqrt" in names
    assert "PI" in names


def test_choose_local_name_simple():
    taken = set()
    name = choose_local_name("_x_value", taken)
    assert name == "_x_value"
    assert name in taken


def test_choose_local_name_suffixing():
    taken = {"_x_value", "_x_value_1", "_x_value_2"}
    name = choose_local_name("_x_value", taken)
    assert name == "_x_value_3"
    assert name in taken


def test_choose_local_name_is_deterministic():
    taken = {"_a", "_a_1"}
    n1 = choose_local_name("_a", taken)
    assert n1 == "_a_2"
    n2 = choose_local_name("_a", taken)
    assert n2 == "_a_3"
