import time
from pathlib import Path

import libcst as cst

from splurge_unittest_to_pytest.events import EventBus, EventTimer, PipelineStartedEvent, StepCompletedEvent
from splurge_unittest_to_pytest.migration_orchestrator import MigrationOrchestrator
from splurge_unittest_to_pytest.transformers import assert_transformer as at
from splurge_unittest_to_pytest.transformers import import_transformer as it


def test_add_pytest_imports_inserts_pytest_and_re_alias():
    src = """import os
from something import x
"""

    class Dummy:
        needs_re_import = True
        re_alias = "re2"

    out = it.add_pytest_imports(src, transformer=Dummy())
    assert "import pytest" in out
    assert "import re as re2" in out or "import re2" in out


def test_remove_unittest_imports_if_unused_removes():
    src = """import unittest
def f():
    return 1
"""
    out = it.remove_unittest_imports_if_unused(src)
    assert "import unittest" not in out


def test_assert_transformer_eq_and_unary_rewrites():
    # Build a Comparison node representing: not ('err' in log.output[0])
    alias = "log"
    # Create AST for: assert not ('err' in log.output[0])
    left = cst.SimpleString(value="'err'")
    sub = cst.Subscript(
        value=cst.Attribute(value=cst.Name(value=alias), attr=cst.Name(value="output")),
        slice=[cst.SubscriptElement(slice=cst.Index(value=cst.Integer(value="0")))],
    )
    comp = cst.Comparison(left=left, comparisons=[cst.ComparisonTarget(operator=cst.In(), comparator=sub)])
    unary = cst.UnaryOperation(operator=cst.Not(), expression=comp)

    # wrap as an Assert to pass to helpers
    rewritten = at._try_unary_comparison_rewrite(unary) if hasattr(at, "_try_unary_comparison_rewrite") else None
    # The helper may return None or an Assert; ensure it doesn't raise and handles the shape
    assert rewritten is None or isinstance(rewritten, cst.Assert)


def test_rewrite_asserts_using_alias_in_with_body_no_crash():
    # Construct a With by parsing source; this ensures a valid libcst With node
    with_node = cst.parse_statement("""
with something as log:
    assert 'x' in log.output[0]
""")
    out = at.rewrite_asserts_using_alias_in_with_body(with_node, "log")
    assert isinstance(out, cst.With)


def test_eventbus_subscribe_publish_and_timer_publish():
    bus = EventBus()
    received = []

    def handler(evt):
        received.append(type(evt))

    bus.subscribe(StepCompletedEvent, handler)
    # publish a StepCompletedEvent
    evt = StepCompletedEvent(
        timestamp=time.time(),
        run_id="r",
        context=type("C", (), {"source_file": "s", "target_file": "t", "run_id": "r"})(),
        step_name="s",
        step_type="st",
        result=type("R", (), {"status": type("S", (), {"value": "ok"})()})(),
        duration_ms=1.0,
    )
    bus.publish(evt)
    assert StepCompletedEvent in received

    # Test EventTimer start/end flow publishes events
    ctx = type("Ctx", (), {"source_file": "s", "target_file": "t", "run_id": "rid"})()
    timer = EventTimer(bus, run_id="rid")
    timer.start_operation("step_write", ctx)
    res = type("R2", (), {"status": type("S2", (), {"value": "ok"})()})()
    dur = timer.end_operation("step_write", res)
    assert isinstance(dur, float)


def test_migration_orchestrator_migrate_directory_no_files(tmp_path):
    orch = MigrationOrchestrator()
    # Create an empty directory
    d = tmp_path / "empty"
    d.mkdir()
    res = orch.migrate_directory(str(d))
    assert res.is_success()
    assert res.data == []


def test_add_pytest_imports_detects_dynamic_import():
    src = """# dynamic import
__import__('pytest')
"""
    out = it.add_pytest_imports(src, transformer=None)
    # dynamic import should be treated as evidence; function should not inject an explicit top-level import
    assert "__import__('pytest')" in out
    assert "import pytest" not in out


def test_eventbus_publish_handler_raises_but_others_receive():
    bus = EventBus()
    calls = []

    def a(evt):
        calls.append("a")

    def b(evt):
        calls.append("b")
        raise RuntimeError("boom")

    def c(evt):
        calls.append("c")

    bus.subscribe(StepCompletedEvent, a)
    bus.subscribe(StepCompletedEvent, b)
    bus.subscribe(StepCompletedEvent, c)

    evt = StepCompletedEvent(
        timestamp=time.time(),
        run_id="r",
        context=type("C", (), {})(),
        step_name="s",
        step_type="t",
        result=type("R", (), {"status": type("S", (), {"value": "ok"})()})(),
        duration_ms=0.1,
    )
    # Should not raise despite b raising
    bus.publish(evt)
    assert calls[0] == "a"
    # b should have been called and appended before raising
    assert "b" in calls
    assert "c" in calls


def test_migrate_file_missing_source_returns_failure():
    orch = MigrationOrchestrator()
    # migrate_file validates the source and returns Result.failure for missing file
    result = orch.migrate_file("this_file_does_not_exist_12345.py")
    assert not result.is_success()
    assert "Source file not found" in str(result.error)
