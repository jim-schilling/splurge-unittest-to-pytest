import textwrap
import libcst as cst
from splurge_unittest_to_pytest.stages import raises_stage


def _has_pytest_with(module: cst.Module) -> bool:
    found = False

    class V(cst.CSTVisitor):
        def visit_With(self, node: cst.With) -> None:
            nonlocal found
            try:
                items = node.items or []
                if not items:
                    return None
                first = items[0]
                call = first.item
                if (
                    isinstance(call, cst.Call)
                    and isinstance(call.func, cst.Attribute)
                    and isinstance(call.func.value, cst.Name)
                    and (call.func.value.value == "pytest")
                ):
                    found = True
            except Exception:
                pass

    module.visit(V())
    return found


def test_enter_with_non_call_item_is_ignored():
    src = textwrap.dedent(
        "\n        # first.item is a Name, not a Call\n        foo = None\n\n        def test_x():\n            with foo as cm:\n                pass\n        "
    )
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    assert out.get("needs_pytest_import") is False
    assert not _has_pytest_with(out["module"])


def test_leave_with_call_but_not_assertRaises_is_ignored():
    src = textwrap.dedent("\n        def test_x_02():\n            with foo():\n                pass\n        ")
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    assert out.get("needs_pytest_import") is False
    assert not _has_pytest_with(out["module"])


def test_simplestatement_call_not_assertRaises_is_not_transformed():
    src = textwrap.dedent("\n        def test_x_03():\n            print('hello')\n        ")
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    assert out.get("needs_pytest_import") is False
    assert not _has_pytest_with(out["module"])
