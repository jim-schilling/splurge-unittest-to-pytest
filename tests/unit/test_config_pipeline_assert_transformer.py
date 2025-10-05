import os
from pathlib import Path

import pytest

from splurge_unittest_to_pytest import config_validation
from splurge_unittest_to_pytest.events import EventBus
from splurge_unittest_to_pytest.pipeline import Job, Pipeline, PipelineFactory, Step, Task
from splurge_unittest_to_pytest.result import Result, ResultStatus


def test_validated_config_basic():
    cfg = config_validation.ValidatedMigrationConfig()
    assert cfg.file_patterns == ["test_*.py"]

    # invalid file_patterns should raise
    with pytest.raises(ValueError):
        config_validation.ValidatedMigrationConfig(file_patterns=[""])


class EchoStep(Step[str, str]):
    def execute(self, context, input_data: str) -> Result[str]:
        return Result.success(input_data + ":ok")


def test_pipeline_success_flow():
    bus = EventBus()
    factory = PipelineFactory(bus)

    step = EchoStep("echo", bus)
    task = factory.create_task("t", [step])
    job = factory.create_job("j", [task])
    pipeline = factory.create_pipeline("p", [job])

    # Create a minimal context stub with run_id
    class Ctx:
        run_id = "r1"

    res = pipeline.execute(Ctx(), initial_input="input")
    assert res.is_success()
    assert res.data == "input:ok"


def test_transformer_caplog_fallback_simple():
    from splurge_unittest_to_pytest.transformers.assert_transformer import (
        transform_caplog_alias_string_fallback,
    )

    src = "with self.assertLogs('x') as log:\n    assert 'oops' in log.output[0]"
    out = transform_caplog_alias_string_fallback(src)
    assert "caplog.records" in out or "caplog.messages" in out
