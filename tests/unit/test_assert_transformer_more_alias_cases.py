from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer


def test_membership_no_subscript_inside_with():
    code = """
def test_in_attr(self):
    with self.assertLogs('my.logger', level='INFO') as log:
        assert 'oops' in log.output
"""
    transformer = UnittestToPytestCstTransformer()
    out = transformer.transform_code(code)
    # should rewrite to caplog.records.getMessage() without subscript or use _caplog.messages
    assert "caplog.records" in out or "caplog.messages" in out
    assert "caplog.messages" in out
    assert "log.output" not in out


def test_self_assert_calls_outside_with_lookahead_variants():
    code = """
def test_outside_self_calls(self):
    with self.assertLogs('my.logger', level='INFO') as log:
        pass

    self.assertEqual(len(log.output), 4)
    self.assertIn('x', log.output)
"""
    transformer = UnittestToPytestCstTransformer()
    out = transformer.transform_code(code)
    # Outside self.assert* calls should be rewritten
    assert "len(caplog.messages)" in out
    assert "caplog.messages" in out
    assert "log.output" not in out


def test_assert_with_subscript_inside_with_variant():
    code = """
def test_subscript_inside(self):
    with self.assertLogs('my.logger', level='INFO') as log:
        assert 'x' in log.output[0]
"""
    transformer = UnittestToPytestCstTransformer()
    out = transformer.transform_code(code)
    assert "caplog.records[0]" in out or "caplog.messages[0]" in out
    assert "caplog.messages" in out
    assert "log.output" not in out
