"""Helpers for converting unittest assertRaises context managers to pytest.raises."""


import libcst as cst

from .call_utils import is_self_call
from .raises import create_pytest_raises_withitem


def convert_assert_raises_with(node: cst.With) -> tuple[cst.With | None, bool]:
    """Convert a `with` node using unittest assertRaises/assertRaisesRegex to a
    `with pytest.raises(...)` node.

    Returns a tuple of (new_with_node or None, needs_pytest_import).
    The helper is pure and does not mutate external state.
    """
    if not node.items:
        return None, False

    item = node.items[0]
    if not isinstance(item.item, cst.Call):
        return None, False

    call_node = item.item

    # Detect self.assertRaises(...) style
    call_info = is_self_call(call_node)
    if call_info:
        method_name, _ = call_info
        if method_name in ("assertRaises", "assertRaisesRegex"):
            new_item = create_pytest_raises_withitem(method_name, call_node.args)
            return node.with_changes(items=[new_item]), True

    # Fallback: if function is a bare Name like assertRaises(...)
    if isinstance(call_node.func, cst.Name):
        method_name = call_node.func.value
        if method_name in ("assertRaises", "assertRaisesRegex"):
            new_item = create_pytest_raises_withitem(method_name, call_node.args)
            return node.with_changes(items=[new_item]), True

    return None, False
