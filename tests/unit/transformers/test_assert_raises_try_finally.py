import textwrap

from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer


def test_try_finally_inner_assert_raises_transformed():
    src = textwrap.dedent(
        """
    def f():
        try:
            # outer try
            try:
                # inner try with with
                with self.assertRaises(ValueError):
                    raise ValueError()
            finally:
                pass
        finally:
            pass
    """
    )

    tr = UnittestToPytestCstTransformer()
    out = tr.transform_code(src)

    assert "pytest.raises" in out
