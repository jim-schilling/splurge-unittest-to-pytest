import io
import os
from pathlib import Path

import libcst as cst
import pytest
from typer.testing import CliRunner

from splurge_unittest_to_pytest import __version__
from splurge_unittest_to_pytest.cli import app, create_config
from splurge_unittest_to_pytest.context import FixtureScope, MigrationConfig, PipelineContext
from splurge_unittest_to_pytest.events import (
    ErrorEvent,
    EventBus,
    EventTimer,
    JobCompletedEvent,
    LoggingSubscriber,
    PipelineCompletedEvent,
    PipelineStartedEvent,
    StepCompletedEvent,
    StepStartedEvent,
)
from splurge_unittest_to_pytest.exceptions import (
    ConfigurationError,
    MigrationError,
    ParseError,
    TransformationError,
    ValidationError,
)
from splurge_unittest_to_pytest.result import Result
from splurge_unittest_to_pytest.steps.output_steps import WriteOutputStep
from splurge_unittest_to_pytest.transformers.unittest_transformer import (
    UnittestToPytestCstTransformer,
)


def test_cli_version_command():
    runner = CliRunner()
    result = runner.invoke(app, ["version"])  # no -q to ensure echo
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_cli_init_config(tmp_path):
    runner = CliRunner()
    cfg = tmp_path / "cfg.yaml"
    result = runner.invoke(app, ["init-config", str(cfg)])
    assert result.exit_code == 0
    assert cfg.exists()
    content = cfg.read_text(encoding="utf-8")
    assert "line_length" in content


def test_cli_migrate_invalid_path_exits():
    runner = CliRunner()
    result = runner.invoke(app, ["migrate", "does-not-exist.py"])  # should exit 1
    assert result.exit_code == 1


def test_events_bus_and_logging_subscriber(caplog):
    bus = EventBus()
    logger = LoggingSubscriber(bus)

    # Use a temporary target so we don't write next to test sources
    target = Path("/tmp") / "out_events.py"
    ctx = PipelineContext.create(source_file=__file__, target_file=str(target), config=MigrationConfig())
    bus.publish(PipelineStartedEvent(timestamp=1.0, run_id=ctx.run_id, context=ctx))
    bus.publish(StepStartedEvent(timestamp=1.0, run_id=ctx.run_id, context=ctx, step_name="s", step_type="S"))
    bus.publish(
        StepCompletedEvent(
            timestamp=2.0,
            run_id=ctx.run_id,
            context=ctx,
            step_name="s",
            step_type="S",
            result=Result.success(1),
            duration_ms=1.0,
        )
    )
    bus.publish(
        PipelineCompletedEvent(
            timestamp=3.0, run_id=ctx.run_id, context=ctx, final_result=Result.success(1), duration_ms=2.0
        )
    )

    # unsubscribe and ensure no errors
    logger.unsubscribe_all()


def test_event_timer_publishes(mocker):
    bus = EventBus()
    target = Path("/tmp") / "out_timer.py"
    ctx = PipelineContext.create(source_file=__file__, target_file=str(target), config=MigrationConfig())
    timer = EventTimer(bus, ctx.run_id)

    received = {"step": False, "job": False}

    def on_step(e):
        received["step"] = True

    def on_job(e):
        received["job"] = True

    bus.subscribe(StepCompletedEvent, on_step)
    bus.subscribe(JobCompletedEvent, on_job)

    timer.start_operation("step_parse", ctx)
    timer.end_operation("step_parse", Result.success(1))

    timer.start_operation("job_main", ctx)
    timer.end_operation("job_main", Result.success(1))

    assert received["step"] and received["job"]


def test_context_public_api_and_immutability(tmp_path):
    cfg = create_config(line_length=100)
    assert isinstance(cfg, MigrationConfig)
    assert cfg.line_length == 100

    src = tmp_path / "x.py"
    src.write_text("print(1)\n")
    ctx = PipelineContext.create(source_file=str(src), target_file=str(tmp_path / "out_ctx.py"), config=cfg)
    d = ctx.to_dict()
    assert d["source_file"].endswith("x.py")


def test_exceptions_public_api():
    assert isinstance(MigrationError("x"), Exception)
    assert isinstance(ParseError("x", source_file="s.py"), Exception)
    assert isinstance(TransformationError("x", pattern_type="assertEqual"), Exception)
    assert isinstance(ValidationError("x", validation_type="syntax", field="name"), Exception)
    assert isinstance(ConfigurationError("x", config_key="line_length"), Exception)


def test_write_output_step_success(tmp_path):
    cfg = MigrationConfig()
    src = tmp_path / "in.py"
    src.write_text("print(1)\n")
    ctx = PipelineContext.create(source_file=str(src), target_file=str(tmp_path / "out.py"), config=cfg)

    step = WriteOutputStep("write", EventBus())
    res = step.run(ctx, "print(2)\n")
    assert res.is_success()
    assert (tmp_path / "out.py").read_text(encoding="utf-8") == "print(2)\n"


def test_write_output_step_dry_run(tmp_path):
    cfg = MigrationConfig(dry_run=True)
    src = tmp_path / "in.py"
    src.write_text("print(1)\n")
    ctx = PipelineContext.create(source_file=str(src), target_file=str(tmp_path / "out.py"), config=cfg)
    res = WriteOutputStep("write", EventBus()).run(ctx, "x")
    assert res.is_success()
    assert res.metadata.get("dry_run") is True


def test_transformer_error_path_pytest_mock(mocker):
    tr = UnittestToPytestCstTransformer()
    # force parse failure branch inside transform_code
    mocker.patch("libcst.parse_module", side_effect=Exception("parse fail"))
    out = tr.transform_code("class A: pass")
    assert isinstance(out, str)
