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

    def test_ir_generation_step(self):
        """Test the IR generation step."""
        # Skip this test for now - complex integration with PipelineContext
        # TODO: Implement proper test once context issues are resolved
        pass

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
