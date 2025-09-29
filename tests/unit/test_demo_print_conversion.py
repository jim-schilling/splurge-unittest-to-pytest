def test_demo_prints_conversion_to_parametrize(capfd):
    """Embed a small unittest.TestCase using self.subTest, convert it, print both versions, and assert parametrize."""
    import sys
    import textwrap

    from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer

    original = textwrap.dedent(
        """
    import unittest


    class MyTests(unittest.TestCase):
        def test_numbers(self):
            test_cases = [(1, True), (0, False), (2, True)]
            for n, expected in test_cases:
                with self.subTest(n=n):
                    assert (n % 2 == 1) == expected

    """
    )

    transformer = UnittestToPytestCstTransformer(parametrize=True)
    converted = transformer.transform_code(original)

    # Write directly to the stdout file descriptor (fd 1). This bypasses
    # Python-level stream wrappers and is more robust against capture/redirect
    # layers introduced by pytest plugins or coverage tooling.
    import os

    sep = b"--- ORIGINAL ---\n"
    os.write(1, sep)
    os.write(1, original.encode("utf-8"))
    os.write(1, b"\n")
    os.write(1, b"--- CONVERTED ---\n")
    os.write(1, converted.encode("utf-8"))
    os.write(1, b"\n")

    # Assert that conversion created a parametrize decorator for the tuple-unpack
    assert "@pytest.mark.parametrize" in converted


def test_parametrize_appends_params_after_self():
    import textwrap

    from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer

    src = textwrap.dedent(
        """
    import unittest


    class T(unittest.TestCase):
        def test_x(self):
            for a, b in [(1, 2), (3, 4)]:
                with self.subTest(a=a):
                    assert a < 10
    """
    )

    out = UnittestToPytestCstTransformer(parametrize=True).transform_code(src)
    assert '@pytest.mark.parametrize("a,b"' in out or "@pytest.mark.parametrize('a,b'" in out
    assert "def test_x(self, a, b)" in out or "def test_x(self, a, b):" in out


def test_existing_non_self_param_inserts_after_existing():
    import textwrap

    from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer

    src = textwrap.dedent(
        """
    import unittest


    class T(unittest.TestCase):
        def test_y(self, extra):
            for n in [1,2]:
                with self.subTest(n=n):
                    assert n < 10
    """
    )

    out = UnittestToPytestCstTransformer(parametrize=True).transform_code(src)
    # signature should keep (self, extra) and then add n after them
    assert "def test_y(self, extra, n)" in out or "def test_y(self, extra, n):" in out


def test_name_collision_gets_suffixed():
    import textwrap

    from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer

    src = textwrap.dedent(
        """
    import unittest


    class T(unittest.TestCase):
        def test_z(self, n):
            for n in [1,2]:
                with self.subTest(n=n):
                    assert n < 10
    """
    )

    out = UnittestToPytestCstTransformer(parametrize=True).transform_code(src)
    # because 'n' exists, the added param should be suffixed to avoid collision
    assert "def test_z(self, n, n_1)" in out or "def test_z(self, n, n_1):" in out


def test_starred_unpack_is_rejected_and_uses_subtests():
    import textwrap

    from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer

    src = textwrap.dedent(
        """
    import unittest


    class T(unittest.TestCase):
        def test_star(self):
            for *rest in [(1,2), (3,4)]:
                with self.subTest(rest=rest):
                    assert True
    """
    )

    out = UnittestToPytestCstTransformer(parametrize=True).transform_code(src)
    # Should NOT parametrize; should rewrite to subtests.test and inject subtests param
    assert "@pytest.mark.parametrize" not in out
    assert "with subtests.test" in out
    assert "def test_star(self, subtests)" in out or "def test_star(self, subtests):" in out
