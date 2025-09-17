import libcst as cst
import pytest

from splurge_unittest_to_pytest.converter import fixtures


def test_create_fixture_with_cleanup_name_collision():
    # If cleanup statements reference the base name, the created local name should be suffixed
    attr = "data"
    # create a cleanup statement that references the base name '_data_value'
    cleanup_stmt = cst.parse_statement("_data_value = 42")
    fn = fixtures.create_fixture_with_cleanup(attr, cst.SimpleString("'x'"), [cleanup_stmt])
    # first body statement is the assignment to the chosen value name
    first = fn.body.body[0]
    assert isinstance(first.body[0], cst.Assign)
    target = first.body[0].targets[0].target
    assert isinstance(target, cst.Name)
    # because _data_value existed the produced name should be suffixed
    assert target.value.startswith("_data_value_")


@pytest.mark.parametrize(
    "expr,should_guard",
    [
        (cst.Name("amb"), True),
        (cst.Attribute(value=cst.Name("self"), attr=cst.Name("amb")), True),
        (cst.Call(func=cst.Name("str"), args=[cst.Arg(value=cst.Name("amb"))]), True),
        (cst.Subscript(value=cst.Name("amb"), slice=[cst.SubscriptElement(slice=cst.Index(cst.Integer("1")))]), True),
        (cst.Tuple(elements=[cst.Element(value=cst.Name("amb"))]), True),
        (cst.Call(func=cst.Name("make")), False),
    ],
)
def test_create_simple_fixture_with_guard_variants(expr, should_guard):
    fn = fixtures.create_simple_fixture_with_guard("amb", expr)
    if should_guard:
        assert any(isinstance(s.body[0], cst.Raise) for s in fn.body.body)
    else:
        assert not any(isinstance(s.body[0], cst.Raise) for s in fn.body.body)


def test_create_fixture_for_attribute_fallbacks_to_simple_when_guard_unavailable(monkeypatch):
    # Simulate import-time NameError in guarded creator by monkeypatching it to raise
    def _raise_name_error(*a, **k):
        raise NameError("simulated")

    monkeypatch.setattr(fixtures, "create_simple_fixture_with_guard", _raise_name_error)
    fn = fixtures.create_fixture_for_attribute("nope", cst.Call(func=cst.Name("make")), {})
    # should be a simple fixture (no Raise in body) and contain a Return
    assert not any(isinstance(s.body[0], cst.Raise) for s in fn.body.body)
    assert any(isinstance(s.body[0], cst.Return) for s in fn.body.body)


def test_infer_float_and_simple_name_behavior():
    ann = fixtures._infer_simple_return_annotation(cst.Float("1.0"))
    assert isinstance(ann.annotation, cst.Name) and ann.annotation.value == "float"

    # simple Name should be treated as simple value by create_simple_fixture
    fn = fixtures.create_simple_fixture("val", cst.Name("some_name"))
    assert any(isinstance(s.body[0], cst.Return) for s in fn.body.body)
    # return uses Name
    ret = fn.body.body[0].body[0]
    assert isinstance(ret, cst.Return) and isinstance(ret.value, cst.Name)


def test_create_simple_fixture_with_guard_call_func_equal_attr_triggers_guard():
    expr = cst.Call(func=cst.Name("amb"))
    fn = fixtures.create_simple_fixture_with_guard("amb", expr)
    assert any(isinstance(s.body[0], cst.Raise) for s in fn.body.body)


def test_autocreated_file_fixture_filename_repr_check():
    fn = fixtures.create_autocreated_file_fixture("sql_file", filename="custom.sql")
    assign = fn.body.body[0]
    call = assign.body[0].value
    # The joinpath arg is a SimpleString with repr(filename)
    argval = call.args[0].value
    assert isinstance(argval, cst.SimpleString)
    assert argval.value == repr("custom.sql")
