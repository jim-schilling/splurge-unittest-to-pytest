#!/usr/bin/env python3
"""Unit tests for IR functionality."""

import libcst as cst
import pytest

from splurge_unittest_to_pytest.ir import Assertion, Expression, TestClass, TestMethod, TestModule
from splurge_unittest_to_pytest.pattern_analyzer import UnittestPatternAnalyzer
from splurge_unittest_to_pytest.steps.ir_generation_step import UnittestToIRStep
from tests.test_utils import assert_code_structure_equals


class TestIRFunctionality:
    """Test the IR functionality."""

    def test_pattern_analyzer_basic(self):
        """Test basic pattern analyzer functionality."""
        code = """
import unittest

class TestExample(unittest.TestCase):
    def test_something(self):
        self.assertEqual(2 + 2, 4)
        self.assertTrue(True)
"""

        analyzer = UnittestPatternAnalyzer()
        ir_module = analyzer.analyze_module(code)

        assert ir_module.name == "test_module"
        assert len(ir_module.classes) == 1
        assert ir_module.classes[0].name == "TestExample"
        assert ir_module.classes[0].is_unittest_class

    def test_ir_generation_step(self, tmp_path):
        """Test the IR generation step."""
        # Create a simple unittest file for testing
        test_file = tmp_path / "test_unittest.py"
        test_file.write_text("""
import unittest

class TestExample(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(1 + 1, 2)
        self.assertTrue(True)

if __name__ == "__main__":
    unittest.main()
""")

        # Create IR generation step
        from splurge_unittest_to_pytest.context import MigrationConfig, PipelineContext
        from splurge_unittest_to_pytest.steps.ir_generation_step import UnittestToIRStep

        config = MigrationConfig()
        step = UnittestToIRStep("ir_generation_step")

        # Parse the code into a CST module
        with open(test_file) as f:
            code = f.read()
        cst_module = cst.parse_module(code)

        # Create pipeline context
        context = PipelineContext.create(source_file=str(test_file), config=config)

        # Execute step
        result = step.execute(context, cst_module)

        # Verify result
        assert result.is_success(), f"IR generation failed: {result.error}"
        ir_module = result.data

        # Verify IR structure
        assert ir_module.name == "test_unittest"
        assert len(ir_module.classes) == 1
        assert ir_module.classes[0].name == "TestExample"
        assert len(ir_module.classes[0].methods) == 1
        assert ir_module.classes[0].methods[0].name == "test_simple"

    def test_module_level_functions_handling(self, tmp_path):
        """Test that module-level functions are properly captured in IR."""
        # Create a unittest file with module-level functions
        test_file = tmp_path / "test_functions.py"
        test_file.write_text("""
import unittest

def helper_function():
    return "helper"

class TestExample(unittest.TestCase):
    def test_simple(self):
        result = helper_function()
        self.assertEqual(result, "helper")

if __name__ == "__main__":
    unittest.main()
""")

        # Analyze the module
        from splurge_unittest_to_pytest.ir import TestModule
        from splurge_unittest_to_pytest.pattern_analyzer import UnittestPatternAnalyzer

        analyzer = UnittestPatternAnalyzer()
        with open(test_file) as f:
            code = f.read()

        ir_module = analyzer.analyze_module(code)

        # Verify module-level function is captured
        assert len(ir_module.standalone_functions) == 1
        assert ir_module.standalone_functions[0].name == "helper_function"
        # Standalone functions don't have is_unittest_method attribute (it's only for test methods)
        # The absence of this attribute indicates it's not a unittest method

    def test_ir_module_getters(self):
        """Test IR module utility methods."""
        ir_module = TestModule(
            name="test",
            imports=[],
            classes=[
                TestClass(
                    name="Test1",
                    base_classes=["unittest.TestCase"],
                    methods=[TestMethod(name="test_method1", body=[Assertion(arguments=[])])],
                    is_unittest_class=True,
                )
            ],
        )

        ir_module.classes[0].needs_pytest_import = True

        assert ir_module.needs_pytest_import
        assert ir_module.get_fixture_count() == 0

    def test_ir_data_model_creation(self):
        """Test creating IR data models manually."""
        # Test Expression
        expr = Expression(type="Call", value="self.assertEqual(a, b)")

        # Test Assertion
        assertion = Assertion(
            arguments=[expr],
            assertion_type=None,  # Will be set properly by analyzer
        )

        # Test TestMethod
        method = TestMethod(name="test_example", body=[assertion])

        # Test TestClass
        test_class = TestClass(
            name="TestExample", base_classes=["unittest.TestCase"], methods=[method], is_unittest_class=True
        )

        # Test TestModule
        module = TestModule(name="test_module", imports=[], classes=[test_class])

        assert module.name == "test_module"
        assert len(module.classes) == 1
        assert module.classes[0].name == "TestExample"
        assert len(module.classes[0].methods) == 1
        assert module.classes[0].methods[0].name == "test_example"
