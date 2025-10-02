import libcst as cst

from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer


def test_transform_does_not_emit_synthetic__caplog_alias():
    src = open("tests/data/unittest_given_complex_01.txt", encoding="utf-8").read()
    t = UnittestToPytestCstTransformer(parametrize=True)
    out = t.transform_code(src)
    # There should be no synthetic alias named _caplog introduced anywhere
    assert "as _caplog" not in out
    # All caplog message access should use caplog.messages, not _caplog.messages
    assert "_caplog.messages" not in out
