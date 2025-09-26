import libcst as cst
import pytest

from splurge_unittest_to_pytest.context import MigrationConfig, PipelineContext
from splurge_unittest_to_pytest.events import EventBus
from splurge_unittest_to_pytest.migration_orchestrator import MigrationOrchestrator
from splurge_unittest_to_pytest.pipeline import Job, Pipeline, PipelineFactory, Step, Task
from splurge_unittest_to_pytest.result import Result, ResultStatus
from splurge_unittest_to_pytest.steps.format_steps import FormatCodeStep, ValidateGeneratedCodeStep
from splurge_unittest_to_pytest.steps.parse_steps import GenerateCodeStep, ParseSourceStep, TransformUnittestStep


class DummyStep(Step[int, int]):
    @staticmethod
    def result_fn(x, ctx):
        from splurge_unittest_to_pytest.result import Result

        if isinstance(x, PipelineContext):
            return Result.success(x)
        if x is None:
            return Result.success(0)
        return Result.success(x + 1)

    def execute(self, context: PipelineContext, input_data: int):
        return DummyStep.result_fn(input_data, context)


def test_parse_steps_public_api():
    config = MigrationConfig()
    context = PipelineContext.create(source_file=__file__, config=config)

    source = """
import unittest
class A(unittest.TestCase):
    def test_x(self):
        self.assertEqual(1,1)
"""
    parse = ParseSourceStep("parse", EventBus())
    tr = TransformUnittestStep("transform", EventBus())
    gen = GenerateCodeStep("generate", EventBus())

    m = parse.run(context, source).unwrap()
    assert isinstance(m, cst.Module)

    m2 = tr.run(context, m).unwrap()
    assert isinstance(m2, cst.Module)

    code = gen.run(context, m2).unwrap()
    assert isinstance(code, str)
    assert "class A" in code


def test_parse_steps_failure_path():
    config = MigrationConfig()
    context = PipelineContext.create(source_file=__file__, config=config)
    bad = "def bad(:\n"
    res = ParseSourceStep("parse", EventBus()).run(context, bad)
    assert res.is_error()


def test_format_steps_public_api():
    config = MigrationConfig(format_code=True, line_length=88)
    context = PipelineContext.create(source_file=__file__, config=config)
    code = "import sys\n\n\nprint(1)\n"

    fmt = FormatCodeStep("format", EventBus())
    val = ValidateGeneratedCodeStep("validate", EventBus())

    formatted = fmt.run(context, code)
    assert formatted.is_success()
    meta = formatted.metadata
    assert meta["isort_applied"] and meta["black_applied"]

    validated = val.run(context, formatted.unwrap())
    assert validated.is_success()


def test_format_steps_warning_on_exception(monkeypatch):
    class FailingFormat(FormatCodeStep):
        def _apply_black(self, code, config):
            raise RuntimeError("black failed")

    config = MigrationConfig(format_code=True)
    context = PipelineContext.create(source_file=__file__, config=config)
    res = FailingFormat("format", EventBus()).run(context, "print(1)\n")
    assert res.is_warning()


def test_pipeline_task_job_public_api():
    bus = EventBus()
    factory = PipelineFactory(bus)

    s1 = factory.create_step("s1", DummyStep)
    s2 = factory.create_step("s2", DummyStep)
    task = factory.create_task("t1", [s1, s2])
    job = factory.create_job("j1", [task])
    pipe = factory.create_pipeline("p1", [job])

    cfg = MigrationConfig()
    ctx = PipelineContext.create(source_file=__file__, config=cfg)

    task_result = task.execute(ctx, 0)
    assert task_result.is_success()
    assert task_result.unwrap() == 2

    job_result = job.execute(ctx)
    assert job_result.is_success()

    pipe_result = pipe.execute(ctx)
    assert pipe_result.is_success()


def test_pipeline_task_error_shortcircuit():
    bus = EventBus()
    factory = PipelineFactory(bus)

    def fail_fn(x, ctx):
        from splurge_unittest_to_pytest.result import Result

        return Result.failure(RuntimeError("boom"))

    DummyStep.result_fn = staticmethod(fail_fn)
    s = factory.create_step("sx", DummyStep)
    t = factory.create_task("tx", [s])
    cfg = MigrationConfig()
    ctx = PipelineContext.create(source_file=__file__, config=cfg)
    res = t.execute(ctx, 0)
    assert res.is_error()


def test_pipeline_task_warning_combined():
    bus = EventBus()
    factory = PipelineFactory(bus)

    def warn_fn(x, ctx):
        from splurge_unittest_to_pytest.result import Result

        return Result.warning(x, ["w1"])  # type: ignore

    DummyStep.result_fn = staticmethod(warn_fn)
    s1 = factory.create_step("w1", DummyStep)
    s2 = factory.create_step("w2", DummyStep)
    t = factory.create_task("tw", [s1, s2])
    cfg = MigrationConfig()
    ctx = PipelineContext.create(source_file=__file__, config=cfg)
    res = t.execute(ctx, 0)
    assert res.is_warning()
    assert res.warnings and len(res.warnings) >= 1


def test_migration_orchestrator_migrate_file_and_directory(tmp_path):
    code = """
import unittest
class T(unittest.TestCase):
    def test_a(self):
        self.assertEqual(1,1)
"""
    src = tmp_path / "t_file.py"
    src.write_text(code)

    orch = MigrationOrchestrator()
    res = orch.migrate_file(str(src))
    assert isinstance(res, Result)

    res_dir = orch.migrate_directory(str(tmp_path))
    assert isinstance(res_dir, Result)
