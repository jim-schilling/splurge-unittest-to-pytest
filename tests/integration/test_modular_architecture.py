#!/usr/bin/env python3
"""Test the new modular architecture."""

from splurge_unittest_to_pytest import MigrationOrchestrator
from splurge_unittest_to_pytest.context import MigrationConfig


def test_modular_architecture():
    """Test that the new modular architecture is working."""
    # Create a migration orchestrator
    orchestrator = MigrationOrchestrator()

    # Test that it has the expected jobs
    assert hasattr(orchestrator, "collector_job")
    assert hasattr(orchestrator, "formatter_job")
    assert hasattr(orchestrator, "output_job")

    # Test that we can create a migration pipeline
    pipeline = orchestrator._create_migration_pipeline()
    assert pipeline.name == "migration"
    # Pipeline now includes collector, formatter and output jobs by default
    assert len(pipeline.jobs) == 3

    # Test basic config creation
    config = MigrationConfig()
    assert config.line_length == 120
    assert config.backup_originals is True

    assert True  # Mark test as successful
