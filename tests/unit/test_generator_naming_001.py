import libcst as cst
from splurge_unittest_to_pytest.stages.generator_parts.filename_inferer import infer_filename_for_local

DOMAINS = ["generator", "naming"]


class Dummy:
    def __init__(self, local_map):
        self.local_assignments = local_map


def test_infer_from_simple_call():
    # local_assignments maps name -> (Call, other)
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
