"""Tests for nested If/For/While control flow handling in the transformer."""

from splurge_unittest_to_pytest.transformers.unittest_transformer import (
    UnittestToPytestCstTransformer,
)


class TestNestedIfForWhile:
    def test_nested_if_for_while_processing(self) -> None:
        """Ensure asserts inside nested If/For/While are transformed and recursion occurs."""
        source = (
            "import unittest\n\n"
            "class T(unittest.TestCase):\n"
            "    def test_nested(self):\n"
            "        for i in range(2):\n"
            "            if i % 2 == 0:\n"
            "                while i < 1:\n"
            "                    self.assertTrue(i == 0)\n"
            "            else:\n"
            "                for j in range(1):\n"
            "                    self.assertEqual(j + 1, 1)\n"
            "        else:\n"
            "            self.assertFalse(False)\n"
        )

        transformer = UnittestToPytestCstTransformer()
        result = transformer.transform_code(source)

        assert isinstance(result, str) and result
        # Core expectations: unittest import removed, assertions rewritten, structure preserved
        assert "import unittest" not in result
        assert "assert " in result
        assert "for i in range(2):" in result
        assert "while i < 1:" in result
        assert "if i % 2 == 0:" in result
        assert "else:" in result
        # Ensure original unittest-style asserts are gone
        assert "self.assertTrue" not in result
        assert "self.assertEqual" not in result
        assert "self.assertFalse" not in result

    def test_loop_orelse_with_assert_raises(self) -> None:
        """Ensure loop orelse bodies are processed and with-assertRaises is rewritten."""
        source = (
            "import unittest\n\n"
            "class T(unittest.TestCase):\n"
            "    def test_for_else_raises(self):\n"
            "        for x in []:\n"
            "            pass\n"
            "        else:\n"
            "            with self.assertRaises(ValueError):\n"
            "                raise ValueError('x')\n"
        )

        transformer = UnittestToPytestCstTransformer()
        result = transformer.transform_code(source)

        assert isinstance(result, str) and result
        # Expect the with self.assertRaises to be converted to pytest.raises in loop orelse
        assert "with pytest.raises(ValueError" in result
        # Ensure unittest import is removed
        assert "import unittest" not in result
