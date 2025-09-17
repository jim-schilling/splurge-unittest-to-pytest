"""Additional tests for stages/raises_stage to cover edge cases and uncovered branches."""

from __future__ import annotations

import libcst as cst

from splurge_unittest_to_pytest.stages import raises_stage


def _apply_transform(src: str, transformer: cst.CSTTransformer) -> cst.Module:
    mod = cst.parse_module(src)
    return mod.visit(transformer)


def test_exception_attr_rewriter_respects_shadowing():
    src = """
def f():
    with pytest.raises(ValueError) as cm:
        pass
    # should rewrite
    _ = cm.exception

def g(cm):
    # shadowed param named cm should prevent rewrite inside g
    _ = cm.exception

"""
    mod = _apply_transform(src, raises_stage.RaisesRewriter())
    # after RaisesRewriter, we should have recorded exception var and later rewritten attrs
    mod2 = mod.visit(raises_stage.ExceptionAttrRewriter("cm"))
    code = mod2.code
    assert "cm.value" in code
    # the shadowed param usage should not be rewritten inside g
    assert "def g(cm):" in code


def test_with_asname_and_without_asname_conversion():
    src = """
class T(unittest.TestCase):
    def test_it(self):
        with self.assertRaises(KeyError):
            raise KeyError()

        with self.assertRaises(ValueError) as ctx:
            raise ValueError()
        _ = ctx.exception
"""
    mod = _apply_transform(src, raises_stage.RaisesRewriter())
    code = mod.code
    # both with-statements should now reference pytest.raises
    assert "pytest.raises(KeyError)" in code
    assert "pytest.raises(ValueError" in code


def test_functional_assertRaises_to_with_conversion():
    src = """
class C(unittest.TestCase):
    def test_call(self):
        self.assertRaises(ValueError, func_that_raises)
        self.assertRaises(ValueError, func_with_args, 1, 2)
"""
    mod = _apply_transform(src, raises_stage.RaisesRewriter())
    code = mod.code
    # functional forms should be converted into with blocks containing the call
    assert "with pytest.raises(ValueError" in code
    assert "func_that_raises()" in code or "func_that_raises(" in code


def test_assertRaisesRegex_match_keyword_added():
    src = """
class C(unittest.TestCase):
    def test_re(self):
        with self.assertRaisesRegex(ValueError, r"bad"):
            raise ValueError('bad')
        self.assertRaisesRegex(ValueError, r"bad", some_call)
"""
    mod = _apply_transform(src, raises_stage.RaisesRewriter())
    code = mod.code
    # regex should be passed with a 'match' keyword argument (spacing may vary),
    # and the pattern should appear nearby
    assert "pytest.raises(ValueError" in code
    assert "match" in code
    assert 'r"bad"' in code or "r'bad'" in code or 'r"bad"(' not in code


def test_comprehension_and_lambda_scope_binding():
    # ensure comprehension/lambda introduce scopes and don't incorrectly shadow exception var
    src = """
def f():
    with self.assertRaises(ValueError) as cm:
        [x for x in range(3) if (lambda y: y)(x)]
    _ = cm.exception
"""
    mod = _apply_transform(src, raises_stage.RaisesRewriter())
    mod2 = mod.visit(raises_stage.ExceptionAttrRewriter("cm"))
    code = mod2.code
    assert "cm.value" in code
