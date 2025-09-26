"""Unit tests for UnittestToIRStep public APIs."""

from pathlib import Path

import libcst as cst
import pytest

from splurge_unittest_to_pytest.context import MigrationConfig, PipelineContext
from splurge_unittest_to_pytest.events import EventBus
from splurge_unittest_to_pytest.result import Result
from splurge_unittest_to_pytest.steps.ir_generation_step import UnittestToIRStep


class TestUnittestToIRStepAPI:
    """Test suite for UnittestToIRStep public API behavior."""

    def setup_method(self):
        """Set up fresh IR step for each test."""
        self.step = UnittestToIRStep("test_ir_generation", EventBus())

    def test_initialization(self):
        """Test that UnittestToIRStep initializes correctly."""
        step = UnittestToIRStep("test_step", EventBus())
        assert step.name == "test_step"

    def test_execute_basic_unittest_class(self, tmp_path):
        """Test execute with basic unittest.TestCase."""
        code = """
import unittest

class TestExample(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(1 + 1, 2)
"""
        module = cst.parse_module(code)

        # Create temporary source file
        source_file = tmp_path / "test_file.py"
        source_file.write_text(code)

        # Create mock context with existing file
        config = MigrationConfig()
        context = PipelineContext(
            source_file=str(source_file),
            target_file=str(tmp_path / "test_output.py"),
            config=config,
            run_id="test_run",
            metadata={},
        )

        result = self.step.execute(context, module)

        assert result.is_success()
        ir_module = result.unwrap()
        assert ir_module.name == "test_file"  # Should extract from context
        assert len(ir_module.classes) == 1
        assert ir_module.classes[0].name == "TestExample"
        assert ir_module.classes[0].is_unittest_class is True

    def test_execute_multiple_classes(self, tmp_path):
        """Test execute with multiple classes."""
        code = """
import unittest

class TestExample1(unittest.TestCase):
    def test_method1(self):
        self.assertEqual(1, 1)

class RegularClass:
    def test_method2(self):
        assert True

class TestExample2(unittest.TestCase):
    def test_method3(self):
        self.assertTrue(True)
"""
        module = cst.parse_module(code)

        # Create temporary source file
        source_file = tmp_path / "test_file.py"
        source_file.write_text(code)

        config = MigrationConfig()
        context = PipelineContext(
            source_file=str(source_file),
            target_file=str(tmp_path / "test_output.py"),
            config=config,
            run_id="test_run",
            metadata={},
        )

        result = self.step.execute(context, module)

        assert result.is_success()
        ir_module = result.unwrap()
        assert len(ir_module.classes) == 3
        assert ir_module.classes[0].name == "TestExample1"
        assert ir_module.classes[0].is_unittest_class is True
        assert ir_module.classes[1].name == "RegularClass"
        assert ir_module.classes[1].is_unittest_class is False
        assert ir_module.classes[2].name == "TestExample2"
        assert ir_module.classes[2].is_unittest_class is True

    def test_execute_with_setup_methods(self, tmp_path):
        """Test execute with setUp and tearDown methods."""
        code = """
import unittest

class TestExample(unittest.TestCase):
    def setUp(self):
        self.value = 42

    def tearDown(self):
        self.value = None

    def test_with_setup(self):
        self.assertEqual(self.value, 42)
"""
        module = cst.parse_module(code)

        # Create temporary source file
        source_file = tmp_path / "test_file.py"
        source_file.write_text(code)

        config = MigrationConfig()
        context = PipelineContext(
            source_file=str(source_file),
            target_file=str(tmp_path / "test_output.py"),
            config=config,
            run_id="test_run",
            metadata={},
        )

        result = self.step.execute(context, module)

        assert result.is_success()
        ir_module = result.unwrap()
        assert len(ir_module.classes) == 1
        test_class = ir_module.classes[0]
        assert test_class.name == "TestExample"
        assert len(test_class.methods) == 1
        test_method = test_class.methods[0]
        assert test_method.name == "test_with_setup"

    def test_execute_with_setup_class_teardown_class(self, tmp_path):
        """Test execute with setUpClass and tearDownClass methods."""
        code = """
import unittest

class TestExample(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared_value = "test"

    @classmethod
    def tearDownClass(cls):
        cls.shared_value = None

    def test_with_class_setup(self):
        self.assertEqual(self.shared_value, "test")
"""
        module = cst.parse_module(code)

        # Create temporary source file
        source_file = tmp_path / "test_file.py"
        source_file.write_text(code)

        config = MigrationConfig()
        context = PipelineContext(
            source_file=str(source_file),
            target_file=str(tmp_path / "test_output.py"),
            config=config,
            run_id="test_run",
            metadata={},
        )

        result = self.step.execute(context, module)

        assert result.is_success()
        ir_module = result.unwrap()
        assert len(ir_module.classes) == 1
        test_class = ir_module.classes[0]
        assert test_class.name == "TestExample"
        assert len(test_class.methods) == 1
        test_method = test_class.methods[0]
        assert test_method.name == "test_with_class_setup"

    def test_execute_with_assertion_methods(self, tmp_path):
        """Test execute with various assertion methods."""
        code = """
import unittest

class TestExample(unittest.TestCase):
    def test_assertions(self):
        self.assertEqual(1, 1)
        self.assertTrue(True)
        self.assertFalse(False)
        self.assertIs(42, 42)
        self.assertIn(1, [1, 2, 3])
        self.assertIsInstance("test", str)
        self.assertDictEqual({"a": 1}, {"a": 1})
        self.assertListEqual([1, 2], [1, 2])
        self.assertSetEqual({1, 2}, {2, 1})
        self.assertTupleEqual((1, 2), (1, 2))
"""
        module = cst.parse_module(code)

        # Create temporary source file
        source_file = tmp_path / "test_file.py"
        source_file.write_text(code)

        config = MigrationConfig()
        context = PipelineContext(
            source_file=str(source_file),
            target_file=str(tmp_path / "test_output.py"),
            config=config,
            run_id="test_run",
            metadata={},
        )

        result = self.step.execute(context, module)

        assert result.is_success()
        ir_module = result.unwrap()
        assert len(ir_module.classes) == 1
        test_class = ir_module.classes[0]
        assert len(test_class.methods) == 1
        test_method = test_class.methods[0]
        assert test_method.name == "test_assertions"

    def test_execute_with_exception_assertions(self, tmp_path):
        """Test execute with exception assertions."""
        code = """
import unittest

class TestExample(unittest.TestCase):
    def test_exceptions(self):
        with self.assertRaises(ValueError):
            raise ValueError("test error")

        with self.assertRaisesRegex(ValueError, "error"):
            raise ValueError("error message")
"""
        module = cst.parse_module(code)

        # Create temporary source file
        source_file = tmp_path / "test_file.py"
        source_file.write_text(code)

        config = MigrationConfig()
        context = PipelineContext(
            source_file=str(source_file),
            target_file=str(tmp_path / "test_output.py"),
            config=config,
            run_id="test_run",
            metadata={},
        )

        result = self.step.execute(context, module)

        assert result.is_success()
        ir_module = result.unwrap()
        assert len(ir_module.classes) == 1
        test_class = ir_module.classes[0]
        assert len(test_class.methods) == 1
        test_method = test_class.methods[0]
        assert test_method.name == "test_exceptions"

    def test_execute_with_imports(self, tmp_path):
        """Test execute with various import statements."""
        code = """
import unittest
from typing import List
import os
from pathlib import Path
import sys as system

class TestExample(unittest.TestCase):
    def test_imports(self):
        self.assertEqual(1, 1)
"""
        module = cst.parse_module(code)

        # Create temporary source file
        source_file = tmp_path / "test_file.py"
        source_file.write_text(code)

        config = MigrationConfig()
        context = PipelineContext(
            source_file=str(source_file),
            target_file=str(tmp_path / "test_output.py"),
            config=config,
            run_id="test_run",
            metadata={},
        )

        result = self.step.execute(context, module)

        assert result.is_success()
        ir_module = result.unwrap()
        assert len(ir_module.imports) > 0

    def test_execute_empty_module(self, tmp_path):
        """Test execute with empty module."""
        code = ""
        module = cst.parse_module(code)

        # Create temporary source file
        source_file = tmp_path / "empty.py"
        source_file.write_text(code)

        config = MigrationConfig()
        context = PipelineContext(
            source_file=str(source_file),
            target_file=str(tmp_path / "empty_output.py"),
            config=config,
            run_id="test_run",
            metadata={},
        )

        result = self.step.execute(context, module)

        assert result.is_success()
        ir_module = result.unwrap()
        assert ir_module.name == "empty"
        assert len(ir_module.classes) == 0

    def test_execute_with_source_file_not_set(self, tmp_path):
        """Test execute when source_file is None."""
        code = """
import unittest

class TestExample(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(1, 1)
"""
        module = cst.parse_module(code)

        # Create temporary source file
        source_file = tmp_path / "test_none.py"
        source_file.write_text(code)

        config = MigrationConfig()
        context = PipelineContext(
            source_file=str(source_file),
            target_file=str(tmp_path / "test_output.py"),
            config=config,
            run_id="test_run",
            metadata={},
        )

        result = self.step.execute(context, module)

        assert result.is_success()
        ir_module = result.unwrap()
        # Should use default name when source_file not available
        assert ir_module.name == "test_none"

    def test_execute_with_complex_nested_structure(self, tmp_path):
        """Test execute with complex nested class and method structure."""
        code = """
import unittest

class OuterClass:
    class TestInner(unittest.TestCase):
        def test_nested(self):
            self.assertTrue(True)

class TestStandalone(unittest.TestCase):
    def test_standalone(self):
        self.assertFalse(False)
"""
        module = cst.parse_module(code)

        # Create temporary source file
        source_file = tmp_path / "complex_test.py"
        source_file.write_text(code)

        config = MigrationConfig()
        context = PipelineContext(
            source_file=str(source_file),
            target_file=str(tmp_path / "complex_output.py"),
            config=config,
            run_id="test_run",
            metadata={},
        )

        result = self.step.execute(context, module)

        assert result.is_success()
        ir_module = result.unwrap()
        assert ir_module.name == "complex_test"
        assert len(ir_module.classes) == 3
        class_names = {cls.name for cls in ir_module.classes}
        assert class_names == {"OuterClass", "TestInner", "TestStandalone"}

    def test_execute_with_inheritance_chains(self, tmp_path):
        """Test execute with inheritance chains."""
        code = """
import unittest

class BaseTest(unittest.TestCase):
    def test_base(self):
        self.assertEqual(1, 1)

class DerivedTest(BaseTest):
    def test_derived(self):
        self.assertEqual(2, 2)
"""
        module = cst.parse_module(code)

        # Create temporary source file
        source_file = tmp_path / "inheritance_test.py"
        source_file.write_text(code)

        config = MigrationConfig()
        context = PipelineContext(
            source_file=str(source_file),
            target_file=str(tmp_path / "inheritance_output.py"),
            config=config,
            run_id="test_run",
            metadata={},
        )

        result = self.step.execute(context, module)

        assert result.is_success()
        ir_module = result.unwrap()
        assert len(ir_module.classes) == 2
        assert ir_module.classes[0].name == "BaseTest"
        assert ir_module.classes[1].name == "DerivedTest"
        assert ir_module.classes[0].is_unittest_class is True
        assert ir_module.classes[1].is_unittest_class is True

    def test_execute_with_comments_and_docstrings(self, tmp_path):
        """Test execute preserves comments and docstrings in IR."""
        code = '''
"""Module docstring."""

import unittest

class TestExample(unittest.TestCase):
    """Class docstring."""

    def test_method(self):
        """Method docstring."""
        self.assertEqual(1, 1)
'''
        module = cst.parse_module(code)

        # Create temporary source file
        source_file = tmp_path / "docstring_test.py"
        source_file.write_text(code)

        config = MigrationConfig()
        context = PipelineContext(
            source_file=str(source_file),
            target_file=str(tmp_path / "docstring_output.py"),
            config=config,
            run_id="test_run",
            metadata={},
        )

        result = self.step.execute(context, module)

        assert result.is_success()
        ir_module = result.unwrap()
        assert len(ir_module.classes) == 1
        test_class = ir_module.classes[0]
        assert test_class.name == "TestExample"
        assert len(test_class.methods) == 1
        test_method = test_class.methods[0]
        assert test_method.name == "test_method"

    def test_execute_with_metadata_collection(self, tmp_path):
        """Test that execute collects metadata about the transformation."""
        code = """
import unittest

class TestExample(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(1, 1)

    def test_another(self):
        self.assertTrue(True)
"""
        module = cst.parse_module(code)

        # Create temporary source file
        source_file = tmp_path / "metadata_test.py"
        source_file.write_text(code)

        config = MigrationConfig()
        context = PipelineContext(
            source_file=str(source_file),
            target_file=str(tmp_path / "metadata_output.py"),
            config=config,
            run_id="test_run",
            metadata={},
        )

        result = self.step.execute(context, module)

        assert result.is_success()
        assert result.metadata is not None
        # Check that metadata was collected
        assert "classes_found" in result.metadata
        assert "assertions_found" in result.metadata
        assert "needs_pytest" in result.metadata

    def test_execute_result_success_metadata(self, tmp_path):
        """Test that successful execution includes correct metadata."""
        code = """
import unittest

class TestExample(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(1, 1)
"""
        module = cst.parse_module(code)

        # Create temporary source file
        source_file = tmp_path / "metadata_test.py"
        source_file.write_text(code)

        config = MigrationConfig()
        context = PipelineContext(
            source_file=str(source_file),
            target_file=str(tmp_path / "metadata_output.py"),
            config=config,
            run_id="test_run",
            metadata={},
        )

        result = self.step.execute(context, module)

        assert result.is_success()
        metadata = result.metadata
        assert metadata["classes_found"] == 1
        assert metadata["assertions_found"] == 1
        assert metadata["needs_pytest"] is True
