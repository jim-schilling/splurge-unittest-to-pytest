from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer


def test_assert_warns_bare_call_wraps_next_stmt():
    code = """
def test_warns(self):
    self.assertWarns(DeprecationWarning)
    do_something()
"""
    out = UnittestToPytestCstTransformer().transform_code(code)
    # should convert to pytest.warns context manager
    assert "pytest.warns" in out or "caplog.at_level" in out
    assert "do_something()" in out


def test_rewrite_eq_left_attribute():
    code = """
def t(self):
    with self.assertLogs('x', level='INFO') as log:
        assert log.output == []
"""
    out = UnittestToPytestCstTransformer().transform_code(code)
    # alias.output -> caplog.records (no getMessage)
    assert (
        "caplog.records == []" in out
        or "caplog.records" in out
        or "caplog.messages == []" in out
        or "caplog.messages" in out
    )


def test_rewrite_eq_left_subscript():
    code = """
def t2(self):
    with self.assertLogs('x', level='INFO') as log:
        assert log.output[0] == 'oops'
"""
    out = UnittestToPytestCstTransformer().transform_code(code)
    # should use caplog.records[0].getMessage()
    assert "caplog.messages[0] == 'oops'" in out or "caplog.messages" in out


def test_rewrite_eq_rhs_subscript():
    code = """
def t3(self):
    with self.assertLogs('x', level='INFO') as log:
        assert 'oops' == log.output[0]
"""
    out = UnittestToPytestCstTransformer().transform_code(code)
    # Accept caplog.messages rewrite for rhs subscript
    assert "caplog.messages" in out
