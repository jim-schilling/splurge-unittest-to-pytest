from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer


def test_preserve_accumulator_and_convert_to_subtests():
    code = """
def test_scenarios(self):
    scenarios = []
    for a, b in [(1, 2), (3, 4)]:
        scenarios.append((a, b))
    for a, b in scenarios:
        with self.subTest(a=a, b=b):
            self.assertEqual(a + b, b + a)
"""
    out = UnittestToPytestCstTransformer().transform_code(code)
    # accumulator should be preserved
    assert "scenarios =" in out
    # self.subTest should be translated to subtests.test
    assert "subtests.test" in out
    # ensure subtests fixture param exists on function signature
    assert "subtests" in out.split("def test_scenarios(")[1].split(")")[0]


def test_literal_loop_gets_parametrized_and_no_subtests_fixture():
    code = """
def test_simple(self):
    for a, b in [(1, 2), (3, 4)]:
        with self.subTest(a=a, b=b):
            self.assertEqual(a + b, b + a)
"""
    out = UnittestToPytestCstTransformer().transform_code(code)
    # Should parametrize the test
    assert "@pytest.mark.parametrize" in out
    # Should not convert to subtests fixture in parametrized output
    assert "subtests.test" not in out
