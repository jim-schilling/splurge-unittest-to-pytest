from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer


def test_with_contains_assert_node_rewrites_len_output():
    code = """
def test_one(self):
    with self.assertLogs('my.logger', level='INFO') as log:
        assert len(log.output) == 2
"""
    transformer = UnittestToPytestCstTransformer()
    out = transformer.transform_code(code)
    # Should use caplog.records and not reference log.output
    assert "caplog.records" in out
    assert "log.output" not in out


def test_with_contains_self_assert_calls_converted():
    code = """
def test_two(self):
    with self.assertLogs('my.logger', level='INFO') as log:
        self.assertEqual(len(log.output), 3)
        self.assertIn('started', log.output[0])
"""
    transformer = UnittestToPytestCstTransformer()
    out = transformer.transform_code(code)
    # assertEqual(len(log.output), N) -> assert len(caplog.records) == N
    assert "len(caplog.records) == 3" in out or "len(caplog.records)" in out
    # membership should be rewritten to getMessage()
    assert ".getMessage()" in out
    assert "log.output" not in out


def test_lookahead_rewrites_following_asserts_outside_with():
    code = """
def test_three(self):
    with self.assertLogs('my.logger', level='INFO') as log:
        pass

    assert len(log.output) == 1
    assert 'oops' in log.output[0]
"""
    transformer = UnittestToPytestCstTransformer()
    out = transformer.transform_code(code)
    # Following assertions should be rewritten to caplog.records and getMessage
    assert "caplog.records" in out
    assert "getMessage" in out
    assert "log.output" not in out
