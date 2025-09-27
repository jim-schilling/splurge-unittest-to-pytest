def test_assert_logs_and_no_logs_string_fallback():
    from splurge_unittest_to_pytest.transformers.assert_transformer import transform_assertions_string_based

    code = """
def test_example(self):
    self.assertLogs('my.logger', 'INFO')
    do_something()
    self.assertNoLogs()
    other_call()
"""

    out = transform_assertions_string_based(code)

    # assertLogs should be converted to a with statement and the following
    # code line should be indented inside it
    assert "with self.assertLogs('my.logger', 'INFO'):" in out
    assert "    do_something()" in out

    # assertNoLogs converted similarly
    assert "with self.assertNoLogs():" in out
    assert "    other_call()" in out
