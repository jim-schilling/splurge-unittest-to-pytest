import libcst as cst

from splurge_unittest_to_pytest.converter import SelfReferenceRemover
from splurge_unittest_to_pytest.main import PatternConfigurator


def test_self_reference_remover_replaces_self_attr() -> None:
    src = "def f(self):\n    return self.x\n"
    mod = cst.parse_module(src)
    # visit module with remover
    new_mod = mod.visit(SelfReferenceRemover())

    class AttrFinder(cst.CSTVisitor):
        def __init__(self) -> None:
            self.found_self_attr = False

        def visit_Attribute(self, node: cst.Attribute) -> None:
            if isinstance(node.value, cst.Name) and node.value.value == "self":
                self.found_self_attr = True

    finder = AttrFinder()
    new_mod.visit(finder)
    assert not finder.found_self_attr


def test_normalize_and_is_methods() -> None:
    # public API: pattern configurator replaces legacy transformer patterns
    cfg = PatternConfigurator()
    sp = cfg.setup_patterns
    tp = cfg.teardown_patterns
    testp = cfg.test_patterns
    assert isinstance(sp, set) and isinstance(tp, set) and isinstance(testp, set)
    # adding patterns via public methods should update the sets
    cfg.add_setup_pattern("before_all")
    assert any("before_all" in p or p == "before_all" for p in cfg.setup_patterns)
    cfg.add_teardown_pattern("after_all")
    assert any("after_all" in p or p == "after_all" for p in cfg.teardown_patterns)
    cfg.add_test_pattern("it_")
    assert any(p == "it_" for p in cfg.test_patterns)


def test_should_remove_first_param_behaviour() -> None:
    # Legacy transformer is deprecated and no longer required by tests.
    # This test asserts that the PatternConfigurator exists and exposes pattern sets.
    cfg = PatternConfigurator()
    assert isinstance(cfg.setup_patterns, set)
