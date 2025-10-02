import textwrap

from splurge_unittest_to_pytest.transformers.assert_transformer import (
    transform_caplog_alias_string_fallback,
    wrap_assert_in_block,
)
from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer

SAMPLE_WITH_ALIAS = textwrap.dedent(
    """
    def test_example(self):
        with self.assertLogs('root', level='INFO') as log:
            assert 'oops' in log.output[0]
    """
)


def test_string_fallback_never_introduces__caplog_alias():
    """Ensure string-level fallback does not insert a synthetic `as _caplog` alias."""
    out = transform_caplog_alias_string_fallback("log.output[0] == 'm'\n")
    assert "as _caplog" not in out


def test_cst_transform_never_emits__caplog_alias():
    """Run the CST transformer on a sample with an alias and assert we never emit `as _caplog`."""
    transformer = UnittestToPytestCstTransformer()
    transformed = transformer.transform_code(SAMPLE_WITH_ALIAS)
    # transformer output should not include a synthetic _caplog alias
    assert "as _caplog" not in transformed


def test_wrap_assert_in_block_no_synthetic_alias_in_generated_with():
    # Use wrap_assert_in_block (libcst helper) to create a With containing caplog call
    stmt = wrap_assert_in_block(["pass"])  # returns list of With nodes or AST nodes
    # When stringified, ensure no 'as _caplog' appears (guard)
    module_code = "".join([getattr(n, "code", str(n)) for n in stmt])
    assert "as _caplog" not in module_code
