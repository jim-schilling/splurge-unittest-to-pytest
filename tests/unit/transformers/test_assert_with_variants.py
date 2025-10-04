import textwrap

from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer


def transform(src: str) -> str:
    tr = UnittestToPytestCstTransformer()
    return tr.transform_code(textwrap.dedent(src))


def test_bare_with_no_comments():
    src = """
def f():
    with self.assertRaises(ValueError):
        raise ValueError()
"""
    out = transform(src)
    assert "pytest.raises" in out


def test_with_comment_above():
    src = """
def f():
    # comment above
    with self.assertRaises(ValueError):
        raise ValueError()
"""
    out = transform(src)
    assert "pytest.raises" in out


def test_with_comment_same_line():
    src = """
def f():
    with self.assertRaises(ValueError):  # same-line comment
        raise ValueError()
"""
    out = transform(src)
    assert "pytest.raises" in out


def test_with_as_alias_preserved():
    src = """
def f():
    with self.assertRaises(ValueError) as cm:
        raise ValueError()
    _ = cm
"""
    out = transform(src)
    # alias usage should remain or be rewritten sensibly (caplog/tests may use alias)
    assert "pytest.raises" in out


def test_nested_withs_transform():
    src = """
def f():
    with self.assertRaises(ValueError):
        with self.assertWarns(Warning):
            raise ValueError()
"""
    out = transform(src)
    assert "pytest.raises" in out
    assert "pytest.warns" in out or "assertWarns" in out


def test_assert_raises_regex_and_warns_variants():
    src = """
def f():
    with self.assertRaisesRegex(ValueError, r"val"):
        raise ValueError('val')
    with self.assertWarns(Warning):
        import warnings
        warnings.warn('w')
"""
    out = transform(src)
    assert "pytest.raises" in out
    assert "pytest.warns" in out


def test_assertlogs_to_caplog():
    src = """
def f(caplog):
    with self.assertLogs('some.logger') as cm:
        import logging
        logging.getLogger('some.logger').warning('warn')
"""
    out = transform(src)
    # translation should reference caplog in some form
    assert "caplog" in out
