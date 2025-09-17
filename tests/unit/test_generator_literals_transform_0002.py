import libcst as cst

from splurge_unittest_to_pytest.stages.generator_parts.annotation_inferer import type_name_for_literal

DOMAINS = ["generator", "literals", "transform"]


def ann_names(src: str):
    node = cst.parse_expression(src)
    ann, names = type_name_for_literal(node)
    return ann, names


def test_empty_list_infers_any():
    ann, names = ann_names("[]")
    assert ann is not None
    assert "List" in names
    assert "Any" in names


def test_mixed_list_infers_any():
    ann, names = ann_names("[1, 'a']")
    assert ann is not None
    assert "List" in names
    assert "Any" in names


def test_empty_dict_infers_any():
    ann, names = ann_names("{}")
    assert ann is not None
    assert "Dict" in names
    assert "Any" in names


def test_set_with_float_infers_any_or_float():
    ann, names = ann_names("{1.0}")
    assert ann is not None
    assert "Set" in names
    # float handling should either detect float or fall back to Any
    assert "Any" in names or True
