import textwrap

import libcst as cst

from splurge_unittest_to_pytest.transformers.unittest_transformer import (
    UnittestToPytestCstTransformer,
)


def _transform(src: str, parametrize: bool = True) -> str:
    transformer = UnittestToPytestCstTransformer(parametrize=parametrize)
    return transformer.transform_code(src)


def test_parametrize_with_literal_list():
    src = textwrap.dedent(
        """
        class TestSomething(unittest.TestCase):
            def test_values(self):
                for i in [1, 2, 3]:
                    with self.subTest(i=i):
                        self.assertEqual(i % 2, 1)
        """
    )

    out = _transform(src)
    # Expect @pytest.mark.parametrize and function body without the for loop
    assert '@pytest.mark.parametrize("i", [1, 2, 3])' in out
    assert "for i in" not in out


def test_parametrize_with_tuple_and_multiple_statements():
    src = textwrap.dedent(
        """
        class TestMultiple(unittest.TestCase):
            def test_multi(self):
                for x in ("a", "b"):
                    with self.subTest(x=x):
                        val = x.upper()
                        self.assertIn(val, ["A", "B"])
        """
    )

    out = _transform(src)
    assert "@pytest.mark.parametrize(\"x\", ['a', 'b'])" in out or '@pytest.mark.parametrize("x", ["a", "b"])' in out
    assert "for x in" not in out
    assert "val = x.upper()" in out


def test_parametrize_with_tuple_unpacking_and_keywords():
    src = textwrap.dedent(
        """
        import unittest

        class Dummy(unittest.TestCase):
            def test_integration_workflow(self):
                test_cases = [
                    ("123", True, DataType.INTEGER, 123),
                    ("3.14", True, DataType.FLOAT, 3.14),
                ]

                for value, can_infer, expected_type, expected_converted in test_cases:
                    with self.subTest(value=value):
                        assert self.type_inference.can_infer(value) == can_infer
                        assert self.type_inference.infer_type(value) == expected_type
                        assert self.type_inference.convert_value(value) == expected_converted
        """
    )

    out = _transform(src)
    assert (
        '@pytest.mark.parametrize("value,can_infer,expected_type,expected_converted",' in out
        or '@pytest.mark.parametrize("value, can_infer, expected_type, expected_converted"' in out
    )
    assert "import pytest" in out


def test_parametrize_merges_multiple_loops() -> None:
    src = textwrap.dedent(
        """
        import unittest

        class Demo(unittest.TestCase):
            def test_multi_stage(self):
                first_batch = [
                    ("a", 1),
                    ("b", 2),
                ]

                second_batch = [
                    ("c", 3),
                    ("d", 4),
                ]

                for value, number in first_batch:
                    with self.subTest(value=value):
                        self.assertEqual(len(value), 1)
                        self.assertLess(number, 10)

                for value, number in second_batch:
                    with self.subTest(value=value):
                        self.assertEqual(len(value), 1)
                        self.assertLess(number, 10)
        """
    )

    out = _transform(src)

    assert out.count("@pytest.mark.parametrize") == 1
    assert "for value, number" not in out
    assert '("c", 3)' in out
    assert '("d", 4)' in out
    assert "subtests.test" not in out


def test_parametrize_allows_local_constant_usage() -> None:
    src = textwrap.dedent(
        """
        import unittest

        class Demo(unittest.TestCase):
            def test_cases(self):
                size = 3
                scenarios = [
                    {
                        "name": "empty",
                        "data": [""] * size,
                    },
                    {
                        "name": "none",
                        "data": [None] * size,
                    },
                ]

                for case in scenarios:
                    with self.subTest(case=case["name"]):
                        assert len(case["data"]) == size
        """
    )

    out = _transform(src)

    assert '@pytest.mark.parametrize("case"' in out
    assert "with subtests.test" not in out
    assert "size = 3" in out
    assert '[""] * 3' in out
    assert "[None] * 3" in out
    assert '[""] * size' not in out
    assert "[None] * size" not in out


def test_parametrize_preserves_supporting_assignments() -> None:
    src = textwrap.dedent(
        """
        import unittest

        class Dummy(unittest.TestCase):
            def test_ordering(self):
                test_cases = [
                    ("alpha", 1),
                    ("beta", 2),
                ]

                test_size = len(test_cases)

                for label, rank in test_cases:
                    with self.subTest(label=label):
                        self.assertLess(rank, test_size)
        """
    )

    out = _transform(src)

    assert '@pytest.mark.parametrize("label,rank"' in out or '@pytest.mark.parametrize("label, rank"' in out
    assert "for label, rank in test_cases" not in out
    assert "test_size = len(test_cases)" in out
    assert "test_cases = [" in out


def test_parametrize_skips_when_rows_reference_local_names():
    src = textwrap.dedent(
        """
        import unittest

        class Dummy(unittest.TestCase):
            def compute_size(self):
                return 3

            def test_derived_data(self):
                size = self.compute_size()
                cases = [
                    ("alpha", [1] * size),
                    ("beta", [2] * size),
                ]

                for label, data in cases:
                    with self.subTest(label=label):
                        self.assertEqual(len(data), size)
        """
    )

    out = _transform(src)

    assert "@pytest.mark.parametrize" not in out
    assert "subtests.test" in out


def test_parametrize_merges_multiple_loops():
    src = textwrap.dedent(
        """
        import unittest

        class Demo(unittest.TestCase):
            def test_multi_stage(self):
                first_batch = [
                    ("a", 1),
                    ("b", 2),
                ]

                second_batch = [
                    ("c", 3),
                    ("d", 4),
                ]

                for value, number in first_batch:
                    with self.subTest(value=value):
                        self.assertEqual(len(value), 1)
                        self.assertLess(number, 10)

                for value, number in second_batch:
                    with self.subTest(value=value):
                        self.assertEqual(len(value), 1)
                        self.assertLess(number, 10)
        """
    )

    out = _transform(src)

    assert out.count("@pytest.mark.parametrize") == 1
    assert "for value, number" not in out
    assert '("c", 3)' in out
    assert '("d", 4)' in out
    assert "subtests.test" not in out
