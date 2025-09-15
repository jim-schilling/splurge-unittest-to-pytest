import libcst as cst
from splurge_unittest_to_pytest.stages.raises_stage import RaisesRewriter

DOMAINS = ["exceptions", "stages"]


def test_rewrites_cm_exception_to_value_for_as_name():
    src = """
class T:
    def test_it(self):
        with self.assertRaises(ValueError) as cm:
            raise ValueError('msg')
        # access
        e = cm.exception
"""
    mod = cst.parse_module(src)
    new = mod.visit(RaisesRewriter())
    code = new.code
    assert "with pytest.raises(ValueError) as cm:" in code
    assert "cm.value" in code


def test_rewrites_in_nested_function_and_comprehension():
    src = """
class T:
    def test_it(self):
        with self.assertRaises(ValueError) as cm:
            raise ValueError('msg')
        def inner():
            return cm.exception
        vals = [cm.exception for _ in range(1)]
        f = lambda: cm.exception
"""
    mod = cst.parse_module(src)
    new = mod.visit(RaisesRewriter())
    code = new.code
    assert "cm.value" in code
    # ensure nested function and comprehension changed
    assert "return cm.value" in code or "cm.value for" in code


def test_does_not_rewrite_when_name_shadowed_in_inner_scopes():
    src = """
class T:
    def test_it(self):
        with self.assertRaises(ValueError) as cm:
            raise ValueError('msg')
        def inner(cm):
            # this parameter should shadow outer cm and keep .exception
            return cm.exception
        vals = [ (lambda cm: cm.exception)(cm) for cm in [cm] ]
        f = lambda cm: cm.exception
"""
    mod = cst.parse_module(src)
    new = mod.visit(RaisesRewriter())
    code = new.code
    # the outer references (outside inner shadowing) should have been rewritten
    assert "with pytest.raises(ValueError) as cm:" in code
    # but inner parameter uses should still refer to .exception (not rewritten)
    # check for at least one inner occurrence left as .exception
    assert "return cm.exception" in code
    assert "lambda cm: cm.exception" in code
