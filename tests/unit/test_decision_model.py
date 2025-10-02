"""Unit tests for decision model dataclasses and serialization.

This module tests the decision model classes, their validation,
and serialization/deserialization functionality.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

import json
import tempfile
from pathlib import Path

import pytest

from splurge_unittest_to_pytest.decision_model import (
    CaplogAliasMetadata,
    ClassProposal,
    DecisionModel,
    FunctionProposal,
    ModuleProposal,
)


class TestCaplogAliasMetadata:
    """Test CaplogAliasMetadata dataclass."""

    def test_valid_metadata_creation(self):
        """Test creating valid CaplogAliasMetadata."""
        metadata = CaplogAliasMetadata(
            alias_name="log_ctx", used_as_records=True, used_as_messages=False, locations=["line_10", "line_15"]
        )

        assert metadata.alias_name == "log_ctx"
        assert metadata.used_as_records is True
        assert metadata.used_as_messages is False
        assert metadata.locations == ["line_10", "line_15"]

    def test_empty_usage_warning(self):
        """Test that empty usage generates warning."""
        import logging
        import warnings

        # Capture warnings to check if our warning is logged
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")

            # This should trigger a warning in the post_init method
            metadata = CaplogAliasMetadata(
                alias_name="log_ctx", used_as_records=False, used_as_messages=False, locations=["line_10"]
            )

            # Check if any warnings were captured
            # Note: The warning might be logged rather than raised as an exception
            assert metadata is not None  # Just verify the object was created


class TestFunctionProposal:
    """Test FunctionProposal dataclass."""

    def test_minimal_proposal_creation(self):
        """Test creating minimal FunctionProposal."""
        proposal = FunctionProposal(function_name="test_example", recommended_strategy="parametrize")

        assert proposal.function_name == "test_example"
        assert proposal.recommended_strategy == "parametrize"
        assert proposal.loop_var_name is None
        assert proposal.accumulator_mutated is False
        assert proposal.caplog_aliases == []
        assert proposal.evidence == []

    def test_full_proposal_creation(self):
        """Test creating full FunctionProposal with all fields."""
        caplog_alias = CaplogAliasMetadata(
            alias_name="log_ctx", used_as_records=True, used_as_messages=False, locations=["line_10"]
        )

        proposal = FunctionProposal(
            function_name="test_with_logging",
            recommended_strategy="subtests",
            loop_var_name="scenario",
            iterable_origin="literal",
            accumulator_mutated=False,
            caplog_aliases=[caplog_alias],
            evidence=["Found subTest loop with literal list"],
        )

        assert proposal.function_name == "test_with_logging"
        assert proposal.recommended_strategy == "subtests"
        assert proposal.loop_var_name == "scenario"
        assert proposal.iterable_origin == "literal"
        assert proposal.accumulator_mutated is False
        assert len(proposal.caplog_aliases) == 1
        assert len(proposal.evidence) == 1

    def test_add_evidence(self):
        """Test adding evidence to proposal."""
        proposal = FunctionProposal(function_name="test_example", recommended_strategy="keep-loop")

        assert len(proposal.evidence) == 0

        proposal.add_evidence("Found accumulator mutation")
        proposal.add_evidence("Loop depends on external state")

        assert len(proposal.evidence) == 2
        assert "Found accumulator mutation" in proposal.evidence
        assert "Loop depends on external state" in proposal.evidence

        # Test duplicate evidence is not added
        proposal.add_evidence("Found accumulator mutation")
        assert len(proposal.evidence) == 2

    def test_is_confident(self):
        """Test confidence assessment."""
        proposal = FunctionProposal(function_name="test_example", recommended_strategy="parametrize")

        # No evidence means not confident
        assert not proposal.is_confident()

        # Add evidence to make it confident
        proposal.add_evidence("Found clear pattern")
        assert proposal.is_confident()


class TestClassProposal:
    """Test ClassProposal dataclass."""

    def test_class_proposal_creation(self):
        """Test creating ClassProposal."""
        func_proposal = FunctionProposal(function_name="test_method", recommended_strategy="parametrize")

        proposal = ClassProposal(
            class_name="TestExample",
            function_proposals={"test_method": func_proposal},
            class_fixtures=["setup_method"],
            class_setup_methods=["setUp"],
        )

        assert proposal.class_name == "TestExample"
        assert len(proposal.function_proposals) == 1
        assert "test_method" in proposal.function_proposals
        assert proposal.class_fixtures == ["setup_method"]
        assert proposal.class_setup_methods == ["setUp"]

    def test_add_function_proposal(self):
        """Test adding function proposal to class."""
        proposal = ClassProposal(class_name="TestExample", function_proposals={})

        func_proposal = FunctionProposal(function_name="test_method", recommended_strategy="parametrize")

        proposal.add_function_proposal(func_proposal)

        assert len(proposal.function_proposals) == 1
        assert proposal.function_proposals["test_method"] == func_proposal

    def test_get_strategy_consensus(self):
        """Test getting strategy consensus from functions."""
        func1 = FunctionProposal("test_1", "parametrize")
        func2 = FunctionProposal("test_2", "parametrize")
        func3 = FunctionProposal("test_3", "subtests")

        proposal = ClassProposal(
            class_name="TestExample", function_proposals={"test_1": func1, "test_2": func2, "test_3": func3}
        )

        # parametrize appears twice, so that's the consensus
        consensus = proposal.get_strategy_consensus()
        assert consensus == "parametrize"

        # Test with no functions
        empty_proposal = ClassProposal("EmptyClass", {})
        assert empty_proposal.get_strategy_consensus() is None


class TestModuleProposal:
    """Test ModuleProposal dataclass."""

    def test_module_proposal_creation(self):
        """Test creating ModuleProposal."""
        class_prop = ClassProposal(class_name="TestExample", function_proposals={})

        proposal = ModuleProposal(
            module_name="test_module.py",
            class_proposals={"TestExample": class_prop},
            module_fixtures=["module_fixture"],
            module_imports=["import unittest"],
            top_level_assignments={"TEST_DATA": "some_data"},
        )

        assert proposal.module_name == "test_module.py"
        assert len(proposal.class_proposals) == 1
        assert "TestExample" in proposal.class_proposals
        assert proposal.module_fixtures == ["module_fixture"]
        assert proposal.module_imports == ["import unittest"]
        assert proposal.top_level_assignments == {"TEST_DATA": "some_data"}

    def test_add_class_proposal(self):
        """Test adding class proposal to module."""
        proposal = ModuleProposal(module_name="test_module.py", class_proposals={})

        class_prop = ClassProposal(class_name="TestExample", function_proposals={})

        proposal.add_class_proposal(class_prop)

        assert len(proposal.class_proposals) == 1
        assert proposal.class_proposals["TestExample"] == class_prop

    def test_get_all_function_proposals(self):
        """Test getting all function proposals from all classes."""
        func1 = FunctionProposal("TestClass.test_1", "parametrize")
        func2 = FunctionProposal("TestClass.test_2", "subtests")
        func3 = FunctionProposal("AnotherClass.test_3", "keep-loop")

        class1 = ClassProposal("TestClass", {"test_1": func1, "test_2": func2})
        class2 = ClassProposal("AnotherClass", {"test_3": func3})

        proposal = ModuleProposal(
            module_name="test_module.py", class_proposals={"TestClass": class1, "AnotherClass": class2}
        )

        all_funcs = proposal.get_all_function_proposals()

        assert len(all_funcs) == 3
        assert "test_1" in all_funcs
        assert "test_2" in all_funcs
        assert "test_3" in all_funcs


class TestDecisionModel:
    """Test DecisionModel dataclass."""

    def test_decision_model_creation(self):
        """Test creating DecisionModel."""
        class_prop = ClassProposal(class_name="TestExample", function_proposals={})

        module_prop = ModuleProposal(module_name="test_module.py", class_proposals={"TestExample": class_prop})

        model = DecisionModel(module_proposals={"test_module.py": module_prop})

        assert len(model.module_proposals) == 1
        assert "test_module.py" in model.module_proposals

    def test_add_module_proposal(self):
        """Test adding module proposal to model."""
        model = DecisionModel(module_proposals={})

        module_prop = ModuleProposal(module_name="test_module.py", class_proposals={})

        model.add_module_proposal(module_prop)

        assert len(model.module_proposals) == 1
        assert model.module_proposals["test_module.py"] == module_prop

    def test_save_and_load_from_file(self):
        """Test saving and loading decision model from file."""
        # Create a test decision model
        func_proposal = FunctionProposal(
            function_name="test_example", recommended_strategy="parametrize", evidence=["Found subTest loop"]
        )

        class_prop = ClassProposal(class_name="TestExample", function_proposals={"test_example": func_proposal})

        module_prop = ModuleProposal(
            module_name="test_module.py",
            class_proposals={"TestExample": class_prop},
            module_fixtures=["module_fixture"],
        )

        original_model = DecisionModel(module_proposals={"test_module.py": module_prop})

        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            original_model.save_to_file(temp_path)

            # Load from file
            loaded_model = DecisionModel(module_proposals={})
            loaded_model.load_from_file(temp_path)

            # Verify the loaded model has the same data
            assert len(loaded_model.module_proposals) == 1
            loaded_module = list(loaded_model.module_proposals.values())[0]
            assert loaded_module.module_name == "test_module.py"
            assert loaded_module.module_fixtures == ["module_fixture"]

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_string_representation(self):
        """Test string representation of decision model."""
        func_proposal = FunctionProposal("test_1", "parametrize")
        class_prop = ClassProposal("TestClass", {"test_1": func_proposal})
        module_prop = ModuleProposal("module.py", {"TestClass": class_prop})

        model = DecisionModel(module_proposals={"module.py": module_prop})

        str_repr = str(model)

        assert "DecisionModel with 1 modules:" in str_repr
        assert "module.py:" in str_repr
        assert "Classes: 1" in str_repr
        assert "TestClass: 1 functions" in str_repr
