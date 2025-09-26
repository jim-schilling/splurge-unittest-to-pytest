"""Data-driven integration tests for unittest to pytest transformation.

This module tests the transformation pipeline using real test data pairs
from tests/data/given_and_expected/ to ensure our implementation produces
the expected pytest output.
"""

import glob
import os
import re
from pathlib import Path

import pytest

from splurge_unittest_to_pytest.cli import create_config, create_event_bus
from splurge_unittest_to_pytest.context import PipelineContext
from splurge_unittest_to_pytest.pipeline import PipelineFactory


class TestDataDrivenTransformation:
    """Test transformations using real data pairs."""

    def get_test_pairs(self):
        """Get all test data pairs."""
        given_pattern = "tests/data/given_and_expected/unittest_given_*.txt"
        expected_pattern = "tests/data/given_and_expected/pytest_expected_*.txt"

        given_files = sorted(glob.glob(given_pattern))
        expected_files = sorted(glob.glob(expected_pattern))

        pairs = []
        for given_file, expected_file in zip(given_files, expected_files, strict=False):
            # Extract test number from filename
            test_num = given_file.split("_")[-1].split(".")[0]
            expected_num = expected_file.split("_")[-1].split(".")[0]

            if test_num == expected_num:
                pairs.append((given_file, expected_file, test_num))

        return pairs

    def test_test_data_exists_and_can_be_processed(self, tmp_path):
        """Test that our test data exists and can be processed by the system.

        This test validates that:
        1. All test data pairs exist
        2. Files can be read successfully
        3. Our transformation pipeline can be initialized
        4. Output files can be written

        Note: This does NOT validate transformation accuracy yet, as we haven't
        implemented the full functionality. That validation will be added later.
        """
        pairs = self.get_test_pairs()

        for given_file, expected_file, test_num in pairs:
            # Read input and expected output
            with open(given_file, encoding="utf-8") as f:
                unittest_code = f.read()

            with open(expected_file, encoding="utf-8") as f:
                expected_pytest_code = f.read()

            # Verify we can read both files
            assert unittest_code, f"unittest file {test_num} is empty"
            assert expected_pytest_code, f"pytest file {test_num} is empty"

            # Create temporary output file
            output_file = tmp_path / f"test_{test_num}_output.py"

            # Create configuration
            config = create_config(format_code=False, dry_run=False, target_directory=str(tmp_path))

            # Create event bus
            event_bus = create_event_bus()

            # Create pipeline factory (we'll need to implement actual pipeline)
            PipelineFactory(event_bus)  # Initialize factory for future use

            # Create pipeline context
            context = PipelineContext.create(source_file=given_file, target_file=str(output_file), config=config)

            # Verify context was created successfully
            assert context.source_file == given_file
            assert context.target_file == str(output_file)
            assert context.config is not None

            # TODO: Implement actual transformation pipeline
            # For now, we'll create a mock transformation
            actual_pytest_code = self.mock_transform(unittest_code)

            # Write actual output
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(actual_pytest_code)

            # Verify file was written
            assert output_file.exists(), f"Output file {output_file} was not created"
            assert output_file.read_text(), f"Output file {output_file} is empty"

    def mock_transform(self, unittest_code: str) -> str:
        """Mock transformation function - replace with actual CST-based pipeline.

        This is a placeholder that demonstrates the pattern. The actual implementation
        will use libcst to parse the Python AST and transform it systematically.

        For now, this just returns a basic structure to show the framework works.
        """
        lines = unittest_code.split("\n")
        transformed_lines = []

        # Add pytest import at the top
        if "import pytest" not in unittest_code:
            transformed_lines.extend(["import pytest", ""])

        # Track setup and teardown code
        setup_code = []
        teardown_code = []
        setup_class_code = []
        teardown_class_code = []
        in_setup = False
        in_teardown = False
        in_setup_class = False
        in_teardown_class = False

        i = 0
        while i < len(lines):
            line = lines[i]
            original_line = line

            # Remove unittest import
            if line.strip() == "import unittest":
                i += 1
                continue
            elif line.strip().startswith("import unittest"):
                i += 1
                continue

            # Remove unittest.TestCase inheritance
            if "(unittest.TestCase)" in line:
                line = line.replace("(unittest.TestCase)", "")

            # Handle setUp method
            elif line.strip() == "def setUp(self):":
                in_setup = True
                i += 1
                continue
            elif in_setup:
                # Collect setup code until next method or class
                if line.strip() and not line.startswith("    def ") and not line.startswith("class "):
                    setup_code.append(line.strip())
                    i += 1
                    continue
                else:
                    in_setup = False

            # Handle tearDown method
            elif line.strip() == "def tearDown(self):":
                in_teardown = True
                i += 1
                continue
            elif in_teardown:
                # Collect teardown code until next method or class
                if line.strip() and not line.startswith("    def ") and not line.startswith("class "):
                    teardown_code.append(line.strip())
                    i += 1
                    continue
                else:
                    in_teardown = False

            # Handle setUpClass method
            elif line.strip() == "def setUpClass(cls):":
                in_setup_class = True
                i += 1
                continue
            elif in_setup_class:
                # Collect setup class code until next method or class
                if line.strip() and not line.startswith("    def ") and not line.startswith("class "):
                    setup_class_code.append(line.strip())
                    i += 1
                    continue
                else:
                    in_setup_class = False

            # Handle tearDownClass method
            elif line.strip() == "def tearDownClass(cls):":
                in_teardown_class = True
                i += 1
                continue
            elif in_teardown_class:
                # Collect teardown class code until next method or class
                if line.strip() and not line.startswith("    def ") and not line.startswith("class "):
                    teardown_class_code.append(line.strip())
                    i += 1
                    continue
                else:
                    in_teardown_class = False

            # Convert assertions - expanded to support more unittest methods
            elif "self.assertEqual(" in line:
                match = re.search(r"self\.assertEqual\(([^,]+),\s*(.+)\)", line.strip())
                if match:
                    actual, expected = match.groups()
                    line = f"        assert {actual} == {expected}"
                else:
                    line = original_line
            elif "self.assertTrue(" in line:
                match = re.search(r"self\.assertTrue\((.+)\)", line.strip())
                if match:
                    condition = match.group(1)
                    line = f"        assert {condition}"
                else:
                    line = original_line
            elif "self.assertFalse(" in line:
                match = re.search(r"self\.assertFalse\((.+)\)", line.strip())
                if match:
                    condition = match.group(1)
                    line = f"        assert not {condition}"
                else:
                    line = original_line
            elif "self.assertIs(" in line:
                match = re.search(r"self\.assertIs\(([^,]+),\s*(.+)\)", line.strip())
                if match:
                    actual, expected = match.groups()
                    line = f"        assert {actual} is {expected}"
                else:
                    line = original_line
            elif "self.assertIsNot(" in line:
                match = re.search(r"self\.assertIsNot\(([^,]+),\s*(.+)\)", line.strip())
                if match:
                    actual, expected = match.groups()
                    line = f"        assert {actual} is not {expected}"
                else:
                    line = original_line
            elif "self.assertIn(" in line:
                match = re.search(r"self\.assertIn\(([^,]+),\s*(.+)\)", line.strip())
                if match:
                    item, container = match.groups()
                    line = f"        assert {item} in {container}"
                else:
                    line = original_line
            elif "self.assertNotIn(" in line:
                match = re.search(r"self\.assertNotIn\(([^,]+),\s*(.+)\)", line.strip())
                if match:
                    item, container = match.groups()
                    line = f"        assert {item} not in {container}"
                else:
                    line = original_line
            elif "self.assertIsNone(" in line:
                match = re.search(r"self\.assertIsNone\((.+)\)", line.strip())
                if match:
                    value = match.group(1)
                    line = f"        assert {value} is None"
                else:
                    line = original_line
            elif "self.assertIsNotNone(" in line:
                match = re.search(r"self\.assertIsNotNone\((.+)\)", line.strip())
                if match:
                    value = match.group(1)
                    line = f"        assert {value} is not None"
                else:
                    line = original_line
            elif "self.assertGreater(" in line:
                match = re.search(r"self\.assertGreater\(([^,]+),\s*(.+)\)", line.strip())
                if match:
                    left, right = match.groups()
                    line = f"        assert {left} > {right}"
                else:
                    line = original_line
            elif "self.assertGreaterEqual(" in line:
                match = re.search(r"self\.assertGreaterEqual\(([^,]+),\s*(.+)\)", line.strip())
                if match:
                    left, right = match.groups()
                    line = f"        assert {left} >= {right}"
                else:
                    line = original_line
            elif "self.assertLess(" in line:
                match = re.search(r"self\.assertLess\(([^,]+),\s*(.+)\)", line.strip())
                if match:
                    left, right = match.groups()
                    line = f"        assert {left} < {right}"
                else:
                    line = original_line
            elif "self.assertLessEqual(" in line:
                match = re.search(r"self\.assertLessEqual\(([^,]+),\s*(.+)\)", line.strip())
                if match:
                    left, right = match.groups()
                    line = f"        assert {left} <= {right}"
                else:
                    line = original_line
            elif "self.assertRaises(" in line:
                match = re.search(r"self\.assertRaises\(([^,]+),\s*(.+)\)", line.strip())
                if match:
                    exception, code = match.groups()
                    line = f"        with pytest.raises({exception}):"
                    # Add indentation to the next line if it's the code to test
                    if i + 1 < len(lines) and lines[i + 1].strip():
                        lines[i + 1] = "            " + lines[i + 1]
                else:
                    line = original_line
            elif "self.assertDictEqual(" in line:
                match = re.search(r"self\.assertDictEqual\(([^,]+),\s*(.+)\)", line.strip())
                if match:
                    first, second = match.groups()
                    line = f"        assert {first} == {second}"
                else:
                    line = original_line
            elif "self.assertTupleEqual(" in line:
                match = re.search(r"self\.assertTupleEqual\(([^,]+),\s*(.+)\)", line.strip())
                if match:
                    first, second = match.groups()
                    line = f"        assert {first} == {second}"
                else:
                    line = original_line
            elif "self.assertSetEqual(" in line:
                match = re.search(r"self\.assertSetEqual\(([^,]+),\s*(.+)\)", line.strip())
                if match:
                    first, second = match.groups()
                    line = f"        assert {first} == {second}"
                else:
                    line = original_line
            elif "self.assertListEqual(" in line:
                match = re.search(r"self\.assertListEqual\(([^,]+),\s*(.+)\)", line.strip())
                if match:
                    first, second = match.groups()
                    line = f"        assert {first} == {second}"
                else:
                    line = original_line
            elif "self.assertRaisesRegex(" in line:
                match = re.search(r"self\.assertRaisesRegex\(([^,]+),\s*([^,]+),\s*(.+)\)", line.strip())
                if match:
                    exception, regex, code = match.groups()
                    line = f"        with pytest.raises({exception}, match={regex}):"
                    # Add indentation to the next line if it's the code to test
                    if i + 1 < len(lines) and lines[i + 1].strip():
                        lines[i + 1] = "            " + lines[i + 1]
                else:
                    line = original_line
            elif "self.assertIsInstance(" in line:
                match = re.search(r"self\.assertIsInstance\(([^,]+),\s*(.+)\)", line.strip())
                if match:
                    obj, class_type = match.groups()
                    line = f"        assert isinstance({obj}, {class_type})"
                else:
                    line = original_line
            elif "self.assertNotIsInstance(" in line:
                match = re.search(r"self\.assertNotIsInstance\(([^,]+),\s*(.+)\)", line.strip())
                if match:
                    obj, class_type = match.groups()
                    line = f"        assert not isinstance({obj}, {class_type})"
                else:
                    line = original_line
            elif "self.assertWarns(" in line:
                match = re.search(r"self\.assertWarns\(([^,]+),\s*(.+)\)", line.strip())
                if match:
                    warning_type, code = match.groups()
                    line = f"        with pytest.warns({warning_type}):"
                    # Add indentation to the next line if it's the code to test
                    if i + 1 < len(lines) and lines[i + 1].strip():
                        lines[i + 1] = "            " + lines[i + 1]
                else:
                    line = original_line
            elif "self.assertWarnsRegex(" in line:
                match = re.search(r"self\.assertWarnsRegex\(([^,]+),\s*([^,]+),\s*(.+)\)", line.strip())
                if match:
                    warning_type, regex, code = match.groups()
                    line = f"        with pytest.warns({warning_type}, match={regex}):"
                    # Add indentation to the next line if it's the code to test
                    if i + 1 < len(lines) and lines[i + 1].strip():
                        lines[i + 1] = "            " + lines[i + 1]
                else:
                    line = original_line
            elif "self.assertLogs(" in line:
                match = re.search(r"self\.assertLogs\(([^,)]+),?\s*([^)]*)\)", line.strip())
                if match:
                    logger_name, level = match.groups()
                    if logger_name and level:
                        line = f"        with self.assertLogs({logger_name}, {level}):"
                    elif logger_name:
                        line = f"        with self.assertLogs({logger_name}):"
                    else:
                        line = "        with self.assertLogs():"
                    # Add indentation to the next line if it's the code to test
                    if i + 1 < len(lines) and lines[i + 1].strip():
                        lines[i + 1] = "            " + lines[i + 1]
                else:
                    line = original_line
            elif "self.assertNoLogs(" in line:
                match = re.search(r"self\.assertNoLogs\(([^,)]+),?\s*([^)]*)\)", line.strip())
                if match:
                    logger_name, level = match.groups()
                    if logger_name and level:
                        line = f"        with self.assertNoLogs({logger_name}, {level}):"
                    elif logger_name:
                        line = f"        with self.assertNoLogs({logger_name}):"
                    else:
                        line = "        with self.assertNoLogs():"
                    # Add indentation to the next line if it's the code to test
                    if i + 1 < len(lines) and lines[i + 1].strip():
                        lines[i + 1] = "            " + lines[i + 1]
                else:
                    line = original_line
            elif "self.assertRegex(" in line:
                match = re.search(r"self\.assertRegex\(([^,]+),\s*([^)]+)\)", line.strip())
                if match:
                    text, pattern = match.groups()
                    line = f"        assert re.search({pattern}, {text})"
                else:
                    line = original_line
            elif "self.assertNotRegex(" in line:
                match = re.search(r"self\.assertNotRegex\(([^,]+),\s*([^)]+)\)", line.strip())
                if match:
                    text, pattern = match.groups()
                    line = f"        assert not re.search({pattern}, {text})"
                else:
                    line = original_line
            elif "self.assertCountEqual(" in line:
                match = re.search(r"self\.assertCountEqual\(([^,]+),\s*(.+)\)", line.strip())
                if match:
                    first, second = match.groups()
                    line = f"        assert collections.Counter({first}) == collections.Counter({second})"
                else:
                    line = original_line
            elif "self.assertMultiLineEqual(" in line:
                match = re.search(r"self\.assertMultiLineEqual\(([^,]+),\s*(.+)\)", line.strip())
                if match:
                    first, second = match.groups()
                    line = f"        assert {first} == {second}"
                else:
                    line = original_line
            elif "self.assertSequenceEqual(" in line:
                match = re.search(r"self\.assertSequenceEqual\(([^,]+),\s*(.+)\)", line.strip())
                if match:
                    first, second = match.groups()
                    line = f"        assert list({first}) == list({second})"
                else:
                    line = original_line

            transformed_lines.append(line)
            i += 1

        # Add fixture if we have setup/teardown code
        if setup_code or teardown_code:
            # Find the class to add the fixture to
            for i, line in enumerate(transformed_lines):
                if line.startswith("class "):
                    # Insert fixture after class declaration
                    fixture_lines = ["    @pytest.fixture(autouse=True)"]
                    fixture_lines.append("    def setup_method(self):")
                    for setup_line in setup_code:
                        fixture_lines.append(f"        {setup_line}")
                    if teardown_code:
                        fixture_lines.append("        yield")
                        for teardown_line in teardown_code:
                            fixture_lines.append(f"        {teardown_line}")
                    else:
                        fixture_lines.append("        pass")
                    transformed_lines[i + 1 : i + 1] = fixture_lines
                    break

        # Clean up empty lines and indentation
        cleaned_lines = []
        for line in transformed_lines:
            # Strip trailing whitespace from each line
            line = line.rstrip()
            if line.strip() or (cleaned_lines and cleaned_lines[-1].strip()):
                # Fix indentation for class methods
                if (
                    line.strip()
                    and not line.startswith("    ")
                    and not line.startswith("import")
                    and not line.startswith("@")
                ):
                    if any(keyword in line for keyword in ["class ", "def ", "@pytest"]):
                        line = line  # Keep as is
                    else:
                        line = "    " + line.lstrip()
                cleaned_lines.append(line)

        # Remove trailing empty lines
        while cleaned_lines and cleaned_lines[-1].strip() == "":
            cleaned_lines.pop()

        return "\n".join(cleaned_lines)

    def test_all_pairs_exist(self):
        """Ensure we have matching pairs for all test cases."""
        pairs = self.get_test_pairs()
        assert len(pairs) > 0, "No test pairs found"

        # Check we have consecutive numbering
        test_numbers = [int(pair[2]) for pair in pairs]
        expected_numbers = list(range(1, len(pairs) + 1))

        assert test_numbers == expected_numbers, (
            f"Missing test numbers. Expected: {expected_numbers}, Got: {test_numbers}"
        )

    @pytest.mark.parametrize("test_num", range(1, 22))  # We have 21 test pairs
    def test_pair_exists(self, test_num):
        """Test that each expected pair exists."""
        given_file = f"tests/data/given_and_expected/unittest_given_{test_num:02d}.txt"
        expected_file = f"tests/data/given_and_expected/pytest_expected_{test_num:02d}.txt"

        assert os.path.exists(given_file), f"Missing given file: {given_file}"
        assert os.path.exists(expected_file), f"Missing expected file: {expected_file}"
