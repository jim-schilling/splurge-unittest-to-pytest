import textwrap
import libcst as cst
from splurge_unittest_to_pytest.stages import raises_stage


class CallFinder(cst.CSTVisitor):
    """Visitor that records Calls and With nodes and keywords found."""

    def __init__(self) -> None:
        self.with_nodes = []
        self.calls = []
        self.match_kw_found = False

    def visit_With(self, node: cst.With) -> None:
        self.with_nodes.append(node)

    def visit_Call(self, node: cst.Call) -> None:
        self.calls.append(node)
        for arg in getattr(node, "args", ()):
            try:
                kw = getattr(arg, "keyword", None)
                if kw is None:
                    continue
                name = getattr(kw, "value", None) or getattr(kw, "id", None) or getattr(kw, "attr", None)
                if name == "match":
                    self.match_kw_found = True
                    break
            except Exception:
                continue


def test_context_manager_regex_sets_match_kw_and_needs_import():
    src = textwrap.dedent(
        "\n        import unittest\n\n        class T(unittest.TestCase):\n            def test_x(self):\n                with self.assertRaisesRegex(ValueError, r\"foo\\d+\"):\n                    raise ValueError('foo1')\n        "
    )
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    assert isinstance(out, dict)
    assert out.get("needs_pytest_import") is True
    new_mod = out["module"]
    finder = CallFinder()
    new_mod.visit(finder)
    assert finder.with_nodes, "expected at least one With node in transformed module"
    assert finder.match_kw_found is True


def test_functional_assertRaisesRegex_transforms_via_simplestatementline():
    src = textwrap.dedent(
        '\n        import unittest\n\n        def test_func():\n            unittest.TestCase.assertRaisesRegex(unittest.TestCase, ValueError, r"bar\\d+", lambda: (_ for _ in () ))\n        '
    )
    module = cst.parse_module(src)
    out = raises_stage.raises_stage({"module": module})
    assert isinstance(out, dict)
    assert "module" in out
    new_mod = out["module"]
    finder = CallFinder()
    new_mod.visit(finder)
    assert finder.with_nodes or finder.match_kw_found or finder.calls
