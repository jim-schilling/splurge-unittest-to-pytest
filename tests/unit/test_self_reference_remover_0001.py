import libcst as cst

from splurge_unittest_to_pytest.converter.helpers import SelfReferenceRemover


def test_leave_attribute_returns_original_when_no_self_or_cls_match() -> None:
    """When the attribute value is not a parameter name (e.g., not 'self'/'cls'),
    the transformer should return the original node to preserve formatting.
    """
    remover = SelfReferenceRemover()

    # Build an attribute like: other.attr (where 'other' is not in param_names)
    original = cst.Attribute(
        value=cst.Name(value="other"),
        attr=cst.Name(value="attr"),
    )

    # Simulate an updated node that might have been produced by other visitors;
    # it should not cause the remover to change the node because the value is
    # not 'self' or 'cls'.
    updated = cst.Attribute(
        value=cst.Name(value="other"),
        attr=cst.Name(value="attr_modified"),
    )

    result = remover.leave_Attribute(original, updated)

    # The transformer should return the original node instance, not the updated
    # node, to avoid unintentional formatting/whitespace changes.
    assert result is original


def test_leave_attribute_returns_attr_when_value_is_self() -> None:
    """When the attribute value is 'self', the transformer should
    strip the instance anchor and return the attribute name node.
    """
    remover = SelfReferenceRemover()

    original = cst.Attribute(
        value=cst.Name(value="self"),
        attr=cst.Name(value="attr"),
    )

    # Simulate an updated node where the attribute name may have been rewritten
    updated = cst.Attribute(
        value=cst.Name(value="self"),
        attr=cst.Name(value="attr_extracted"),
    )

    result = remover.leave_Attribute(original, updated)

    # When the attribute value is self/cls, the remover should return the
    # attribute node (a cst.Name) extracted from the updated attribute.
    assert isinstance(result, cst.Name)
    assert result.value == "attr_extracted"


def test_leave_attribute_returns_attr_when_value_is_cls() -> None:
    """Ensure 'cls' is handled like 'self' and the attribute name is returned."""
    remover = SelfReferenceRemover()

    original = cst.Attribute(
        value=cst.Name(value="cls"),
        attr=cst.Name(value="klass"),
    )

    updated = cst.Attribute(
        value=cst.Name(value="cls"),
        attr=cst.Name(value="klass_extracted"),
    )

    result = remover.leave_Attribute(original, updated)

    assert isinstance(result, cst.Name)
    assert result.value == "klass_extracted"
