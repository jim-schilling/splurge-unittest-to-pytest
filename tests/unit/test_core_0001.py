"""Tests for the unittest to pytest converter."""

import pytest
from pathlib import Path
from splurge_unittest_to_pytest import convert_string
import re
from splurge_unittest_to_pytest.stages.generator_parts import GeneratorCore
import libcst as cst


class TestBasicAssertions:
    """Test conversion of basic unittest assertions."""

    def test_assert_equal_conversion(self) -> None:
        unittest_code = "\nimport unittest\n\nclass TestExample(unittest.TestCase):\n    def test_something(self) -> None:\n        self.assertEqual(1 + 1, 2)\n"
        result = convert_string(unittest_code)
        assert result.has_changes
        assert "assert 1 + 1 == 2" in result.converted_code
        assert "assertEqual" not in result.converted_code

    def test_assert_true_conversion(self) -> None:
        unittest_code = "\nimport unittest\n\nclass TestExample(unittest.TestCase):\n    def test_something(self) -> None:\n        self.assertTrue(True)\n"
        result = convert_string(unittest_code)
        assert result.has_changes
        assert "assert True" in result.converted_code
        assert "assertTrue" not in result.converted_code

    def test_assert_false_conversion(self) -> None:
        unittest_code = "\nimport unittest\n\nclass TestExample(unittest.TestCase):\n    def test_something(self) -> None:\n        self.assertFalse(False)\n"
        result = convert_string(unittest_code)
        assert result.has_changes
        assert "assert not False" in result.converted_code
        assert "assertFalse" not in result.converted_code

    def test_assert_is_none_conversion(self) -> None:
        unittest_code = "\nimport unittest\n\nclass TestExample(unittest.TestCase):\n    def test_something(self) -> None:\n        self.assertIsNone(None)\n"
        result = convert_string(unittest_code)
        assert result.has_changes
        assert "assert None is None" in result.converted_code
        assert "assertIsNone" not in result.converted_code

    def test_assert_in_conversion(self) -> None:
        unittest_code = "\nimport unittest\n\nclass TestExample(unittest.TestCase):\n    def test_something(self) -> None:\n        self.assertIn(1, [1, 2, 3])\n"
        result = convert_string(unittest_code)
        assert result.has_changes
        assert "assert 1 in [1, 2, 3]" in result.converted_code
        assert "assertIn" not in result.converted_code

    def test_assert_is_instance_conversion(self) -> None:
        unittest_code = "\nimport unittest\n\nclass TestExample(unittest.TestCase):\n    def test_something(self) -> None:\n        self.assertIsInstance(1, int)\n"
        result = convert_string(unittest_code)
        assert result.has_changes
        assert "assert isinstance(1, int)" in result.converted_code
        assert "assertIsInstance" not in result.converted_code

    def test_assert_greater_conversion(self) -> None:
        """Test assertGreater conversion to assert ... > ..."""
        unittest_code = "\nimport unittest\n\nclass TestExample(unittest.TestCase):\n    def test_something(self) -> None:\n        self.assertGreater(2, 1)\n"
        result = convert_string(unittest_code)
        assert result.has_changes
        assert "assert 2 > 1" in result.converted_code
        assert "assertGreater" not in result.converted_code

    def test_assert_less_equal_conversion(self) -> None:
        """Test assertLessEqual conversion to assert ... <= ..."""
        unittest_code = "\nimport unittest\n\nclass TestExample(unittest.TestCase):\n    def test_something(self) -> None:\n        self.assertLessEqual(2, 2)\n"
        result = convert_string(unittest_code)
        assert result.has_changes
        assert "assert 2 <= 2" in result.converted_code
        assert "assertLessEqual" not in result.converted_code

    def test_assert_not_equal_conversion(self) -> None:
        """Test assertNotEqual conversion to assert !=."""
        unittest_code = "\nimport unittest\n\nclass TestExample(unittest.TestCase):\n    def test_something(self) -> None:\n        self.assertNotEqual(1, 2)\n"
        result = convert_string(unittest_code)
        assert result.has_changes
        assert "assert 1 != 2" in result.converted_code
        assert "assertNotEqual" not in result.converted_code

    def test_assert_is_not_none_conversion(self) -> None:
        """Test assertIsNotNone conversion to assert ... is not None."""
        unittest_code = "\nimport unittest\n\nclass TestExample(unittest.TestCase):\n    def test_something(self) -> None:\n        self.assertIsNotNone(42)\n"
        result = convert_string(unittest_code)
        assert result.has_changes
        assert "assert 42 is not None" in result.converted_code
        assert "assertIsNotNone" not in result.converted_code

    def test_assert_not_in_conversion(self) -> None:
        """Test assertNotIn conversion to assert ... not in ..."""
        unittest_code = "\nimport unittest\n\nclass TestExample(unittest.TestCase):\n    def test_something(self) -> None:\n        self.assertNotIn(4, [1, 2, 3])\n"
        result = convert_string(unittest_code)
        assert result.has_changes
        assert "assert 4 not in [1, 2, 3]" in result.converted_code
        assert "assertNotIn" not in result.converted_code

    def test_assert_not_is_instance_conversion(self) -> None:
        """Test assertNotIsInstance conversion to assert not isinstance(...)."""
        unittest_code = '\nimport unittest\n\nclass TestExample(unittest.TestCase):\n    def test_something(self) -> None:\n        self.assertNotIsInstance("hello", int)\n'
        result = convert_string(unittest_code)
        assert result.has_changes
        assert 'assert not isinstance("hello", int)' in result.converted_code
        assert "assertNotIsInstance" not in result.converted_code

    def test_assert_greater_equal_conversion(self) -> None:
        """Test assertGreaterEqual conversion to assert ... >= ..."""
        unittest_code = "\nimport unittest\n\nclass TestExample(unittest.TestCase):\n    def test_something(self) -> None:\n        self.assertGreaterEqual(2, 2)\n"
        result = convert_string(unittest_code)
        assert result.has_changes
        assert "assert 2 >= 2" in result.converted_code
        assert "assertGreaterEqual" not in result.converted_code

    def test_assert_less_conversion(self) -> None:
        """Test assertLess conversion to assert ... < ..."""
        unittest_code = "\nimport unittest\n\nclass TestExample(unittest.TestCase):\n    def test_something(self) -> None:\n        self.assertLess(1, 2)\n"
        result = convert_string(unittest_code)
        assert result.has_changes
        assert "assert 1 < 2" in result.converted_code
        assert "assertLess" not in result.converted_code


class TestExceptionHandling:
    """Test conversion of exception handling assertions."""

    def test_assert_raises_conversion(self) -> None:
        """Test assertRaises conversion to pytest.raises context manager."""
        unittest_code = '\nimport unittest\n\nclass TestExample(unittest.TestCase):\n    def test_something(self) -> None:\n        with self.assertRaises(ValueError):\n            raise ValueError("test")\n'
        result = convert_string(unittest_code)
        assert result.has_changes
        assert "with pytest.raises(ValueError):" in result.converted_code
        assert "assertRaises" not in result.converted_code

    def test_assert_raises_regex_conversion(self) -> None:
        """Test assertRaisesRegex conversion to pytest.raises with match parameter."""
        unittest_code = '\nimport unittest\n\nclass TestExample(unittest.TestCase):\n    def test_something(self) -> None:\n        with self.assertRaisesRegex(ValueError, "test"):\n            raise ValueError("test message")\n'
        result = convert_string(unittest_code)
        assert result.has_changes
        assert 'with pytest.raises(ValueError, match = "test"):' in result.converted_code
        assert "assertRaisesRegex" not in result.converted_code


class TestClassStructure:
    """Test conversion of class structure elements."""

    def test_unittest_testcase_removal(self) -> None:
        """Test removal of unittest.TestCase inheritance."""
        unittest_code = "\nimport unittest\n\nclass TestExample(unittest.TestCase):\n    def test_something(self) -> None:\n        self.assertTrue(True)\n"
        result = convert_string(unittest_code)
        assert result.has_changes
        assert "class TestExample():" not in result.converted_code
        assert "unittest.TestCase" not in result.converted_code
        assert "def test_something(" in result.converted_code

    def test_setup_method_conversion(self) -> None:
        """Test setUp method conversion to pytest fixture."""
        unittest_code = "\nimport unittest\n\nclass TestExample(unittest.TestCase):\n    def setUp(self) -> None:\n        self.value = 42\n    \n    def test_something(self) -> None:\n        self.assertEqual(self.value, 42)\n"
        result = convert_string(unittest_code)
        assert result.has_changes
        assert "@pytest.fixture" in result.converted_code
        assert "def value(" in result.converted_code
        assert "def setUp_fixture():" not in result.converted_code
        assert "autouse=True" not in result.converted_code
        assert "def test_something(value):" in result.converted_code

    def test_teardown_method_conversion(self) -> None:
        """Test tearDown method conversion to pytest fixture with yield."""
        unittest_code = "\nimport unittest\n\nclass TestExample(unittest.TestCase):\n    def setUp(self) -> None:\n        self.value = 42\n        \n    def tearDown(self) -> None:\n        pass\n    \n    def test_something(self) -> None:\n        self.assertTrue(True)\n"
        result = convert_string(unittest_code)
        assert result.has_changes
        assert "@pytest.fixture" in result.converted_code
        assert "def value(" in result.converted_code
        assert "def tearDown_fixture():" not in result.converted_code
        assert "autouse=True" not in result.converted_code
        assert "def test_something(value):" in result.converted_code

    def test_setup_teardown_fixture_integration(self) -> None:
        """Test setUp/tearDown conversion to proper pytest fixtures with parameters."""
        unittest_code = '\nimport os\nimport shutil\nimport tempfile\nimport unittest\n\nfrom splurge_sql_generator.schema_parser import SchemaParser\n\n\nclass TestSchemaParser(unittest.TestCase):\n    def setUp(self) -> None:\n        self.parser = SchemaParser()\n        self.temp_dir = tempfile.mkdtemp()\n\n    def tearDown(self) -> None:\n        shutil.rmtree(self.temp_dir, ignore_errors=True)\n        \n    def test_load_sql_type_mapping_default(self) -> None:\n        yaml_content = "..."\n        yaml_file = os.path.join(self.temp_dir, "sql_type.yaml")\n        with open(yaml_file, "w", encoding="utf-8") as f:\n            f.write(yaml_content)\n\n        parser_instance = SchemaParser(sql_type_mapping_file=yaml_file)\n        mapping = parser_instance._sql_type_mapping\n'
        result = convert_string(unittest_code)
        assert result.has_changes
        assert "@pytest.fixture" in result.converted_code
        assert "autouse=True" not in result.converted_code
        assert "def parser(" in result.converted_code
        assert "def temp_dir(" in result.converted_code
        assert "def setUp_fixture():" not in result.converted_code
        assert "def tearDown_fixture():" not in result.converted_code
        assert "def test_load_sql_type_mapping_default(parser, temp_dir):" in result.converted_code
        assert "yield temp_dir" in result.converted_code or "yield" in result.converted_code

    def test_teardown_triggers_yield_fixture_for_temp_dir(self) -> None:
        """Ensure tearDown calling shutil.rmtree(self.temp_dir) produces a yield fixture."""
        unittest_code = "\nimport os\nimport shutil\nimport tempfile\nimport unittest\n\n\nclass TestExample(unittest.TestCase):\n    def setUp(self) -> None:\n        self.temp_dir = tempfile.mkdtemp()\n\n    def tearDown(self) -> None:\n        shutil.rmtree(self.temp_dir, ignore_errors=True)\n\n    def test_something(self) -> None:\n        assert True\n"
        result = convert_string(unittest_code)
        assert result.has_changes
        assert "def temp_dir():" in result.converted_code
        assert "yield temp_dir" in result.converted_code or "yield" in result.converted_code


class TestImportHandling:
    """Test handling of import statements."""

    def test_unittest_import_removal(self) -> None:
        """Test removal of unittest imports."""
        unittest_code = "\nimport unittest\n\nclass TestExample(unittest.TestCase):\n    def test_something(self) -> None:\n        self.assertTrue(True)\n"
        result = convert_string(unittest_code)
        assert result.has_changes
        assert "import unittest" not in result.converted_code
        assert "unittest" not in result.converted_code

    def test_pytest_import_addition(self) -> None:
        """Test addition of pytest import when needed."""
        unittest_code = '\nimport unittest\n\nclass TestExample(unittest.TestCase):\n    def test_something(self) -> None:\n        with self.assertRaises(ValueError):\n            raise ValueError("test")\n'
        result = convert_string(unittest_code)
        assert result.has_changes
        assert "import pytest" in result.converted_code


class TestComplexScenarios:
    """Test conversion of complex test scenarios."""

    def test_complete_test_class_conversion(self) -> None:
        """Test conversion of a complete test class."""
        unittest_code = "\nimport unittest\n\nclass TestExample(unittest.TestCase):\n    def setUp(self) -> None:\n        self.value = 42\n    \n    def test_addition(self) -> None:\n        self.assertEqual(self.value + 1, 43)\n    \n    def test_boolean(self) -> None:\n        self.assertTrue(self.value > 0)\n    \n    def tearDown(self) -> None:\n        self.value = None\n"
        result = convert_string(unittest_code)
        assert result.has_changes
        assert "import pytest" in result.converted_code
        assert "class TestExample():" not in result.converted_code
        assert "@pytest.fixture" in result.converted_code
        assert "def value(" in result.converted_code
        assert "yield 42" in result.converted_code
        assert "value = None" in result.converted_code
        assert "def test_addition(value):" in result.converted_code
        assert "def test_boolean(value):" in result.converted_code
        assert "assert value + 1 == 43" in result.converted_code
        assert "assert value > 0" in result.converted_code

    def test_no_changes_needed(self) -> None:
        """Test that pure pytest code is left unchanged."""
        pytest_code = "\nimport pytest\n\ndef test_example():\n    assert True\n\n@pytest.fixture\ndef sample_fixture():\n    return 42\n"
        result = convert_string(pytest_code)
        assert not result.has_changes
        assert result.converted_code == pytest_code

    def test_mixed_assertions(self) -> None:
        """Test conversion of mixed assertion types."""
        unittest_code = "\nimport unittest\n\nclass TestExample(unittest.TestCase):\n    def test_mixed(self) -> None:\n        self.assertEqual(1, 1)\n        self.assertTrue(True)\n        self.assertIsNone(None)\n        self.assertIn(1, [1, 2, 3])\n        self.assertGreater(2, 1)\n"
        result = convert_string(unittest_code)
        assert result.has_changes
        assert "assert 1 == 1" in result.converted_code
        assert "assert True" in result.converted_code
        assert "assert None is None" in result.converted_code
        assert "assert 1 in [1, 2, 3]" in result.converted_code
        assert "assert 2 > 1" in result.converted_code


class TestErrorHandling:
    """Test error handling for malformed code."""

    def test_invalid_syntax(self) -> None:
        """Test handling of code with syntax errors."""
        invalid_code = "\nimport unittest\n\nclass TestExample(unittest.TestCase\n    def test_something(self) -> None:\n        self.assertTrue(True)\n"
        result = convert_string(invalid_code)
        assert not result.has_changes
        assert len(result.errors) > 0
        assert "Failed to parse" in result.errors[0]
        assert result.converted_code == invalid_code


class TestExampleFiles:
    """Test conversion of example unittest files to ensure they compile after conversion."""

    @pytest.mark.parametrize("filename", [f"unittest_{i:02d}.txt" for i in range(1, 31)])
    def test_conversion_compiles(self, filename: str, tmp_path: Path) -> None:
        """Test that converted code from example files compiles without syntax errors."""
        example_path = Path(__file__).parent.parent / "data" / filename
        with open(example_path, "r") as f:
            unittest_code = f.read()
        result = convert_string(unittest_code)
        converted_file = tmp_path / f"converted_{filename.replace('.txt', '.py')}"
        converted_file.write_text(result.converted_code)
        try:
            compile(result.converted_code, str(converted_file), "exec")
        except SyntaxError as e:
            pytest.fail(f"Converted code from {filename} has syntax error: {e}")
        assert "unittest.TestCase" not in result.converted_code, (
            f"unittest.TestCase inheritance should be removed from {filename}"
        )
        assert "self.assert" not in result.converted_code, f"self.assert should be converted in {filename}"
        assert result.has_changes, f"Expected changes for {filename}"


class TestMixedUnittestPytestFiles:
    """Test conversion of files containing both unittest and pytest code."""

    @pytest.mark.parametrize("filename", [f"unittest_pytest_{i:02d}.txt" for i in range(1, 26)])
    def test_mixed_conversion(self, filename: str, tmp_path: Path) -> None:
        """Test that unittest parts are converted while pytest parts remain unchanged."""
        example_path = Path(__file__).parent.parent / "data" / filename
        with open(example_path, "r") as f:
            mixed_code = f.read()
        result = convert_string(mixed_code)
        converted_file = tmp_path / f"converted_{filename.replace('.txt', '.py')}"
        converted_file.write_text(result.converted_code)
        try:
            compile(result.converted_code, str(converted_file), "exec")
        except SyntaxError as e:
            pytest.fail(f"Converted code from {filename} has syntax error: {e}")
        assert "unittest.TestCase" not in result.converted_code, (
            f"unittest.TestCase inheritance should be removed from {filename}"
        )
        assert "self.assert" not in result.converted_code, f"self.assert should be converted in {filename}"
        assert (
            "import pytest" in result.converted_code
            or "@pytest." in result.converted_code
            or "pytest." in result.converted_code
            or ("def test_" in result.converted_code)
        ), f"pytest code should remain in {filename}"
        assert result.has_changes, f"Expected changes for mixed file {filename}"


UNITTEST_SRC = '\nimport os\nimport shutil\nimport tempfile\nimport unittest\nfrom pathlib import Path\nfrom splurge_sql_generator import generate_class, generate_multiple_classes\nfrom tests.unit.test_utils import create_sql_with_schema\n\nclass TestInitAPI(unittest.TestCase):\n    def setUp(self):\n        # Create temporary directory for this test\n        self.temp_dir = tempfile.mkdtemp()\n        self.sql_content = """# TestClass\\n# test_method\\nSELECT 1;"""\n        \n        # Use the shared helper function\n        sql_file, schema_file = create_sql_with_schema(\n            Path(self.temp_dir), \n            "test.sql", \n            self.sql_content\n        )\n        self.sql_file = str(sql_file)\n        self.schema_file = str(schema_file)\n\n    def tearDown(self):\n        # Clean up the entire temp directory\n        shutil.rmtree(self.temp_dir, ignore_errors=True)\n\n    def test_generate_class(self):\n        code = generate_class(self.sql_file, schema_file_path=self.schema_file)\n        self.assertIn(\'class TestClass\', code)\n\n    def test_generate_multiple_classes(self):\n        self.output_dir = self.sql_file + \'_outdir\'\n        os.mkdir(self.output_dir)\n        result = generate_multiple_classes([self.sql_file], output_dir=self.output_dir, schema_file_path=self.schema_file)\n        self.assertIn(\'TestClass\', result)\n\n'


def test_converted_fixtures_return_paths():
    converted = convert_string(UNITTEST_SRC)
    output = converted.converted_code
    assert "def sql_file(" in output or "def sql_file(" in output
    bare_return_re = re.compile("return\\s+['\\\"]test\\.sql['\\\"]")
    assert not bare_return_re.search(output), "Converted fixture 'sql_file' should not return bare 'test.sql'"
    path_expr_ok = any(
        (
            token in output
            for token in ["Path(temp_dir) / 'test.sql'", 'Path(temp_dir) / "test.sql"', "path.write_text(sql_content)"]
        )
    )
    if not path_expr_ok:
        assert "create_sql_with_schema(" in output, (
            "Converted output should create/write the test file under temp_dir and return its path, or preserve the helper call that produces it"
        )


def test_generator_core_make_fixture():
    gc = GeneratorCore()
    src = gc.make_fixture("my_fixture", "    return 1")
    code = cst.Module([src]).code if not isinstance(src, str) else str(src)
    assert "def my_fixture" in code
    src2 = gc.make_fixture("my_fixture", "    return 2")
    code2 = cst.Module([src2]).code if not isinstance(src2, str) else str(src2)
    assert "def my_fixture_2" in code2
