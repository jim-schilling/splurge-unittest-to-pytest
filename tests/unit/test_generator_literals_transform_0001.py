import libcst as cst
from splurge_unittest_to_pytest.stages.generator_parts.annotation_inferer import type_name_for_literal

DOMAINS = ["generator", "literals", "transform"]


def parse(src: str):
    return cst.parse_expression(src)


def ann_names(node):
    ann, names = type_name_for_literal(node)
    return ann, set(names)


def test_list_infer():
    ann, names = ann_names(parse('["a", "b"]'))
    assert ann is not None
    assert "List" in names


def test_tuple_infer():
    ann, names = ann_names(parse('(1, "a")'))
    assert ann is not None
    assert "Tuple" in names


def test_dict_infer():
    ann, names = ann_names(parse('{"k": 1}'))
    assert ann is not None
    assert "Dict" in names


def test_non_literal_returns_none():
    ann, names = ann_names(parse("foo()"))
    assert ann is None
    assert names == set()
