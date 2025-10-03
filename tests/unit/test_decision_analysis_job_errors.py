"""Error-coverage tests for decision_analysis_job steps.

These tests exercise failure branches and ensure steps return Result.failure
with appropriate error types and metadata rather than raising uncaught
exceptions in the test runner.
"""

from __future__ import annotations

import libcst as cst

from splurge_unittest_to_pytest.context import MigrationConfig, PipelineContext
from splurge_unittest_to_pytest.events import EventBus
from splurge_unittest_to_pytest.jobs.decision_analysis_job import (
    ClassScannerStep,
    ModuleScannerStep,
    ParseSourceForAnalysisStep,
    ProposalReconcilerStep,
)
from splurge_unittest_to_pytest.result import Result


def test_parse_source_for_analysis_step_invalid_source() -> None:
    step = ParseSourceForAnalysisStep("parse_test", EventBus())
    context = PipelineContext.create(source_file="temp.py")

    # invalid python should cause a failure Result
    result = step.execute(context, "this is not valid python ((")
    assert result.is_error()


def test_module_scanner_handles_internal_exception(monkeypatch) -> None:
    step = ModuleScannerStep("module_scan", EventBus())

    # Create a simple valid module
    module = cst.parse_module("import os\n")

    # Monkeypatch helper to raise
    def _bad_collect_imports(self, module_arg):
        raise RuntimeError("boom")

    monkeypatch.setattr(ModuleScannerStep, "_collect_imports", _bad_collect_imports, raising=True)

    context = PipelineContext(
        source_file="test.py",
        target_file=None,
        config=MigrationConfig(),
        run_id="r",
        metadata={"cst_module": module},
    )

    result = step.execute(context, module)
    assert result.is_error()


def test_class_scanner_missing_module_proposal_key() -> None:
    # When metadata lacks the 'module_proposal' key entirely, the step should error
    step = ClassScannerStep("class_scan", EventBus())
    module = cst.parse_module("class X: pass")

    context = PipelineContext(
        source_file="test.py",
        target_file=None,
        config=MigrationConfig(),
        run_id="r",
        metadata={"cst_module": module},
    )

    result = step.execute(context, module)
    assert result.is_error()


def test_proposal_reconciler_handles_reconcile_exception(monkeypatch) -> None:
    step = ProposalReconcilerStep("reconcile", EventBus())
    module = cst.parse_module("class X: pass")

    # Create a module_proposal-like object but patch _reconcile_class_proposals to raise
    class DummyModuleProposal:
        def __init__(self):
            self.class_proposals = {"X": object()}

    monkeypatch.setattr(
        ProposalReconcilerStep,
        "_reconcile_class_proposals",
        lambda self, a, b: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    context = PipelineContext(
        source_file="test.py",
        target_file=None,
        config=MigrationConfig(),
        run_id="r",
        metadata={"module_proposal": DummyModuleProposal(), "cst_module": module},
    )

    result = step.execute(context, module)
    assert result.is_error()
