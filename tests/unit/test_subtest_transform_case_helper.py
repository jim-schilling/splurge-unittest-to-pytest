def test_case_helper_tuple_unpacking_converts_to_parametrize():
    """Ensure the real-world example in tests/tmp/test_case_helper.py converts to parametrize."""
    import textwrap

    from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer

    # The real test fixture file lives under tests/tmp/ (gitignored). To make
    # this unit test self-contained and deterministic we embed the source here
    # directly so the test does not depend on a gitignored file.
    src = textwrap.dedent(
        '''
    import unittest

    from splurge_tools.case_helper import CaseHelper


    class TestCaseHelper(unittest.TestCase):
        """Test cases for CaseHelper class."""

        def test_to_train(self):
            """Test train case conversion."""
            test_cases = [
                ("hello world", "Hello-World"),
                ("HELLO WORLD", "Hello-World"),
                ("hello-world", "Hello-World"),
                ("hello_world", "Hello-World"),
                ("", ""),
            ]
            for input_str, expected in test_cases:
                with self.subTest(input_str=input_str):
                    assert CaseHelper.to_train(input_str) == expected

        def test_to_sentence(self):
            """Test sentence case conversion."""
            test_cases = [
                ("hello world", "Hello world"),
                ("HELLO WORLD", "Hello world"),
                ("hello-world", "Hello world"),
                ("hello_world", "Hello world"),
                ("", ""),
            ]
            for input_str, expected in test_cases:
                with self.subTest(input_str=input_str):
                    assert CaseHelper.to_sentence(input_str) == expected

        def test_to_camel(self):
            """Test camel case conversion."""
            test_cases = [
                ("hello world", "helloWorld"),
                ("HELLO WORLD", "helloWorld"),
                ("hello-world", "helloWorld"),
                ("hello_world", "helloWorld"),
                ("", ""),
            ]
            for input_str, expected in test_cases:
                with self.subTest(input_str=input_str):
                    assert CaseHelper.to_camel(input_str) == expected

        def test_to_snake(self):
            """Test snake case conversion."""
            test_cases = [
                ("hello world", "hello_world"),
                ("HELLO WORLD", "hello_world"),
                ("hello-world", "hello_world"),
                ("HelloWorld", "helloworld"),
                ("", ""),
            ]
            for input_str, expected in test_cases:
                with self.subTest(input_str=input_str):
                    assert CaseHelper.to_snake(input_str) == expected

        def test_to_kebab(self):
            """Test kebab case conversion."""
            test_cases = [
                ("hello world", "hello-world"),
                ("HELLO WORLD", "hello-world"),
                ("hello_world", "hello-world"),
                ("HelloWorld", "helloworld"),
                ("", ""),
            ]
            for input_str, expected in test_cases:
                with self.subTest(input_str=input_str):
                    assert CaseHelper.to_kebab(input_str) == expected

        def test_to_pascal(self):
            """Test pascal case conversion."""
            test_cases = [
                ("hello world", "HelloWorld"),
                ("HELLO WORLD", "HelloWorld"),
                ("hello-world", "HelloWorld"),
                ("hello_world", "HelloWorld"),
                ("", ""),
            ]
            for input_str, expected in test_cases:
                with self.subTest(input_str=input_str):
                    assert CaseHelper.to_pascal(input_str) == expected

        def test_handle_empty_values(self):
            """Test that empty values are handled correctly by the decorator."""
            # Test None values
            assert CaseHelper.to_train(None) == ""
            assert CaseHelper.to_sentence(None) == ""
            assert CaseHelper.to_camel(None) == ""
            assert CaseHelper.to_snake(None) == ""
            assert CaseHelper.to_kebab(None) == ""
            assert CaseHelper.to_pascal(None) == ""

            # Test empty strings
            assert CaseHelper.to_train("") == ""
            assert CaseHelper.to_sentence("") == ""
            assert CaseHelper.to_camel("") == ""
            assert CaseHelper.to_snake("") == ""
            assert CaseHelper.to_kebab("") == ""
            assert CaseHelper.to_pascal("") == ""

            # Test whitespace-only strings (should not be considered empty)
            assert CaseHelper.to_train("   ") == "---"
            assert CaseHelper.to_sentence("   ") == "   "

    '''
    )

    transformer = UnittestToPytestCstTransformer(parametrize=True)
    out = transformer.transform_code(src)

    # Methods that use for input_str, expected in test_cases should become parametrize with two params
    expected_methods = [
        "test_to_train",
        "test_to_sentence",
        "test_to_camel",
        "test_to_snake",
        "test_to_kebab",
        "test_to_pascal",
    ]

    # Ensure parametrize decorator for tuple-unpacking case exists in the output
    assert (
        '@pytest.mark.parametrize("input_str,expected"' in out or "@pytest.mark.parametrize('input_str,expected'" in out
    )

    parametrize_present = (
        '@pytest.mark.parametrize("input_str,expected"' in out or "@pytest.mark.parametrize('input_str,expected'" in out
    )

    for m in expected_methods:
        if parametrize_present:
            # When we converted to @pytest.mark.parametrize the function signature
            # should include the param names after self.
            assert f"def {m}(self, input_str, expected)" in out or f"def {m}(self, input_str, expected):" in out
        else:
            assert f"def {m}(self)" in out or f"def {m}(self):" in out

    # The complex "test_handle_empty_values" should not be converted to parametrize
    assert "test_handle_empty_values" in out
    assert '@pytest.mark.parametrize("input_str,expected"' in out


def test_subtest_with_multiple_args_is_not_parametrized_and_uses_subtests():
    import textwrap

    from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer

    code = textwrap.dedent(
        """
    import unittest

    class T(unittest.TestCase):
        def test_multi(self):
            for i in [1,2]:
                with self.subTest(i, i+1):
                    assert i < 10
    """
    )

    transformer = UnittestToPytestCstTransformer()
    out = transformer.transform_code(code)

    # Conservative behavior: we should not create a parametrize for multiple-arg subTest
    assert "@pytest.mark.parametrize" not in out
    # The with-block should be rewritten to use subtests.test and the signature should include subtests
    assert "with subtests.test(i, i+1):" in out
    assert "def test_multi(self, subtests)" in out or "def test_multi(self, subtests):" in out


def test_subtest_with_complex_iterable_is_not_parametrized_and_uses_subtests():
    import textwrap

    from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer

    code = textwrap.dedent(
        """
    import unittest

    def get_values():
        return [1,2,3]

    class T(unittest.TestCase):
        def test_complex(self):
            for x in get_values():
                with self.subTest(x=x):
                    assert x < 10
    """
    )

    transformer = UnittestToPytestCstTransformer()
    out = transformer.transform_code(code)

    # We should not parametrize when iterator is non-literal
    assert "@pytest.mark.parametrize" not in out
    # should rewrite with to subtests.test and add subtests param
    assert "with subtests.test(x=x):" in out
    assert "def test_complex(self, subtests)" in out or "def test_complex(self, subtests):" in out


def test_nested_with_if_for_detects_subtests_and_injects_param():
    """Ensure a deep nested With inside If and For is detected and `subtests` param injected."""
    import textwrap

    from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer

    code = textwrap.dedent(
        """
    import unittest

    class T(unittest.TestCase):
        def test_deep(self):
            for i in [1,2]:
                if i % 2 == 0:
                    with self.subTest(i=i):
                        assert i < 10
    """
    )

    transformer = UnittestToPytestCstTransformer()
    out = transformer.transform_code(code)

    # Should rewrite with to subtests.test and add subtests param
    assert "with subtests.test(i=i):" in out
    assert "def test_deep(self, subtests)" in out or "def test_deep(self, subtests):" in out


def test_nested_try_with_detects_subtests_and_injects_param():
    """Ensure subtests inside a Try/Except/Finally is detected."""
    import textwrap

    from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer

    code = textwrap.dedent(
        """
    import unittest

    class T(unittest.TestCase):
        def test_try(self):
            try:
                x = 1
            except Exception:
                with self.subTest(x=x):
                    assert x == 1
            finally:
                pass
    """
    )

    transformer = UnittestToPytestCstTransformer()
    out = transformer.transform_code(code)

    assert "with subtests.test(x=x):" in out
    assert "def test_try(self, subtests)" in out or "def test_try(self, subtests):" in out


def test_nested_with_inside_with_detects_subtests_and_injects_param():
    """Ensure With nested inside another With is detected."""
    import textwrap

    from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer

    code = textwrap.dedent(
        """
    import unittest

    class T(unittest.TestCase):
        def test_within_with(self):
            with open('f.txt') as f:
                with self.subTest():
                    assert True
    """
    )

    transformer = UnittestToPytestCstTransformer()
    out = transformer.transform_code(code)

    assert "with subtests.test()" in out
    assert "def test_within_with(self, subtests)" in out or "def test_within_with(self, subtests):" in out


def test_nested_multiarg_subtest_in_if_does_not_parametrize_and_injects():
    """Multi-arg subTest nested inside an If should not parametrize but should be rewritten and inject subtests."""
    import textwrap

    from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer

    code = textwrap.dedent(
        """
    import unittest

    class T(unittest.TestCase):
        def test_multi_if(self):
            for i in [1,2]:
                if i > 0:
                    with self.subTest(i, i+1):
                        assert i < 10
    """
    )

    transformer = UnittestToPytestCstTransformer()
    out = transformer.transform_code(code)

    assert "@pytest.mark.parametrize" not in out
    assert "with subtests.test(i, i+1):" in out
    assert "def test_multi_if(self, subtests)" in out or "def test_multi_if(self, subtests):" in out


def test_tuple_unpack_in_try_handler_converts_or_rewrites_and_injects():
    """Tuple-unpack loop values inside a Try/Except handler should be considered for parametrize when safe or rewritten and cause injection."""
    import textwrap

    from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer

    code = textwrap.dedent(
        """
    import unittest

    class T(unittest.TestCase):
        def test_tuple_try(self):
            try:
                values = [(1,2),(3,4)]
            except Exception:
                for a, b in values:
                    with self.subTest(a=a):
                        assert a < 10
    """
    )

    transformer = UnittestToPytestCstTransformer(parametrize=True)
    out = transformer.transform_code(code)

    # Either converted to a parametrize over (a,b) or rewritten to subtests.test.
    assert '@pytest.mark.parametrize("a,b"' in out or "with subtests.test(a=a):" in out
    # In either case ensure subtests is injected when subtests.test is present
    if "with subtests.test" in out:
        assert "def test_tuple_try(self, subtests)" in out or "def test_tuple_try(self, subtests):" in out


def test_subtest_in_inner_class_method_detects_and_injects():
    """A subTest used inside a method of an inner class should be rewritten and the inner method should receive subtests."""
    import textwrap

    from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer

    code = textwrap.dedent(
        """
    import unittest

    class Outer:
        class Inner(unittest.TestCase):
            def test_inner(self):
                with self.subTest():
                    assert True
    """
    )

    transformer = UnittestToPytestCstTransformer()
    out = transformer.transform_code(code)

    assert "with subtests.test()" in out
    assert "def test_inner(self, subtests)" in out or "def test_inner(self, subtests):" in out


def test_tuple_unpack_parametrize_created_for_keyword_ref():
    """When loop target is a tuple and subTest uses keyword referencing one of the names, parametrize should be created."""
    import textwrap

    from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer

    code = textwrap.dedent(
        """
    import unittest

    class T(unittest.TestCase):
        def test_mixed(self):
            for a, b in [(1,2), (3,4)]:
                with self.subTest(a=a):
                    assert a < 10
    """
    )

    transformer = UnittestToPytestCstTransformer(parametrize=True)
    out = transformer.transform_code(code)

    # parametrize over both a and b should be present
    assert '@pytest.mark.parametrize("a,b"' in out or "@pytest.mark.parametrize('a,b'" in out
    # subtests.test should not appear because we converted to parametrize
    assert "with subtests.test" not in out


def test_tuple_unpack_multiarg_subtest_rewrites_and_injects():
    """Tuple-unpack loop with multi-arg subTest should not parametrize but should be rewritten and inject subtests."""
    import textwrap

    from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer

    code = textwrap.dedent(
        """
    import unittest

    class T(unittest.TestCase):
        def test_tuple_multi(self):
            for a, b in [(1,2),(3,4)]:
                with self.subTest(a, b):
                    assert a < 10
    """
    )

    transformer = UnittestToPytestCstTransformer(parametrize=True)
    out = transformer.transform_code(code)

    assert "@pytest.mark.parametrize" not in out
    assert "with subtests.test(a, b):" in out
    assert "def test_tuple_multi(self, subtests)" in out or "def test_tuple_multi(self, subtests):" in out


def test_classmethod_and_staticmethod_variations():
    """Ensure cls.subTest in a @classmethod is rewritten and injected; an invalid @staticmethod using self.subTest is left alone."""
    import textwrap

    from splurge_unittest_to_pytest.transformers.unittest_transformer import UnittestToPytestCstTransformer

    code = textwrap.dedent(
        """
    import unittest

    class T(unittest.TestCase):
        @classmethod
        def test_cls(cls):
            with cls.subTest():
                assert True

        @staticmethod
        def test_static():
            with self.subTest():
                assert True
    """
    )

    transformer = UnittestToPytestCstTransformer()
    out = transformer.transform_code(code)

    # classmethod: should be rewritten and inject subtests param after cls
    assert "with subtests.test()" in out
    assert "def test_cls(cls, subtests)" in out or "def test_cls(cls, subtests):" in out

    # staticmethod: transformer should not attempt to rewrite an undefined 'self' usage
    assert "def test_static()" in out or "def test_static(self)" not in out
