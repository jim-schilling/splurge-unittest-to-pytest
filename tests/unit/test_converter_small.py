import libcst as cst

from splurge_unittest_to_pytest.converter import SelfReferenceRemover, UnittestToPytestTransformer


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
    # public API: properties and add_* methods
    t = UnittestToPytestTransformer(compat=False)
    # ensure public pattern properties exist
    sp = t.setup_patterns
    tp = t.teardown_patterns
    testp = t.test_patterns
    assert isinstance(sp, set) and isinstance(tp, set) and isinstance(testp, set)
    # adding patterns via public methods should update the sets
    t.add_setup_pattern("before_all")
    assert any("before_all" in p or p == "before_all" for p in t.setup_patterns)
    t.add_teardown_pattern("after_all")
    assert any("after_all" in p or p == "after_all" for p in t.teardown_patterns)
    t.add_test_pattern("it_")
    assert any(p == "it_" for p in t.test_patterns)


def test_should_remove_first_param_behaviour() -> None:
    # Ensure instantiation emits a DeprecationWarning (public behavior)
    import warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        _ = UnittestToPytestTransformer(compat=False)
        assert any(isinstance(x.message, DeprecationWarning) for x in w)
