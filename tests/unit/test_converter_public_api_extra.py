import libcst as cst

from splurge_unittest_to_pytest.converter import UnittestToPytestTransformer


def test_pattern_adders_and_properties():
    t = UnittestToPytestTransformer(compat=False)
    # default patterns exist
    assert 'setUp' in t.setup_patterns or 'setup' in t.setup_patterns
    # add custom patterns
    t.add_setup_pattern('mySetup')
    t.add_teardown_pattern('myTeardown')
    t.add_test_pattern('my_test_')
    assert any(p.lower() == 'mysetup' for p in t.setup_patterns)
    assert any(p.lower() == 'myteardown' for p in t.teardown_patterns)
    assert any(p == 'my_test_' for p in t.test_patterns)


def test_remove_self_references_delegation():
    # create a simple function with self.x used in body
    src = """
def test_fn(self):
    print(self.x)
"""
    node = cst.parse_module(src).body[0]
    assert isinstance(node, cst.FunctionDef)

    t = UnittestToPytestTransformer(compat=False)
    new_params, new_body = t._remove_method_self_references(node)
    # new_params should be a list (self removed)
    assert isinstance(new_params, list)
    assert isinstance(new_body, cst.BaseSuite)


def test_normalize_method_name_delegation():
    t = UnittestToPytestTransformer(compat=False)
    # current normalization converts camelCase to snake with underscore
    assert t._normalize_method_name('setUp') == 'set_up'
