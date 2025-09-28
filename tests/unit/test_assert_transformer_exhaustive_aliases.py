from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer


def _transform(code: str) -> str:
    return UnittestToPytestCstTransformer().transform_code(code)


def test_len_attribute_inside_with():
    code = """
def t1(self):
    with self.assertLogs('x', level='INFO') as log:
        assert len(log.output) == 2
"""
    out = _transform(code)
    assert "caplog.records" in out
    assert "len(caplog.records)" in out


def test_len_subscript_inside_with():
    code = """
def t2(self):
    with self.assertLogs('x', level='INFO') as log:
        assert len(log.output[0]) == 1
"""
    out = _transform(code)
    assert "caplog.records[0]" in out
    assert "len(caplog.records[0])" in out


def test_membership_attribute_inside_with():
    code = """
def t3(self):
    with self.assertLogs('x', level='INFO') as log:
        assert 'a' in log.output
"""
    out = _transform(code)
    assert "caplog.records" in out
    assert ".getMessage()" in out


def test_membership_subscript_inside_with():
    code = """
def t4(self):
    with self.assertLogs('x', level='INFO') as log:
        assert 'b' in log.output[1]
"""
    out = _transform(code)
    assert "caplog.records[1]" in out
    assert ".getMessage()" in out


def test_self_assert_equal_subscript_and_in():
    code = """
def t5(self):
    with self.assertLogs('x', level='INFO') as log:
        pass

    self.assertEqual(len(log.output[0]), 5)
    self.assertIn('z', log.output)
"""
    out = _transform(code)
    assert "len(caplog.records[0])" in out or "len(caplog.records)" in out
    assert "caplog.records" in out
