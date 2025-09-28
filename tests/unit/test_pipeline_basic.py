from splurge_unittest_to_pytest.context import PipelineContext
from splurge_unittest_to_pytest.pipeline import Job, Pipeline, Step, Task
from splurge_unittest_to_pytest.result import Result, ResultStatus


class DummyEventBus:
    def __init__(self):
        self.published = []

    def publish(self, event):
        self.published.append(event)


class AddOneStep(Step):
    def execute(self, context: PipelineContext, input_data: int) -> Result[int]:
        return Result.success(input_data + 1)


class FailStep(Step):
    def execute(self, context: PipelineContext, input_data: int) -> Result[int]:
        return Result.failure(RuntimeError("boom"))


def make_context(tmp_path=None):
    # create temp files so PipelineContext validation accepts the source path
    if tmp_path is None:
        from pathlib import Path

        tf = Path(".") / "__fixture_dummy__.py"
        tf.write_text("x=1\n")
        source = str(tf)
    else:
        p = tmp_path / "s.py"
        p.write_text("x=1\n")
        source = str(p)

    return PipelineContext.create(source_file=source, target_file=None, config=None, run_id="test")


def test_task_happy_path(tmp_path):
    eb = DummyEventBus()
    s1 = AddOneStep("s1", eb)
    s2 = AddOneStep("s2", eb)
    task = Task("t", [s1, s2], eb)
    res = task.execute(make_context(tmp_path), 0)
    assert not res.is_error()
    assert res.data == 2


def test_task_failure_short_circuits(tmp_path):
    eb = DummyEventBus()
    ok = AddOneStep("ok", eb)
    bad = FailStep("bad", eb)
    t = Task("t2", [ok, bad, ok], eb)
    res = t.execute(make_context(tmp_path), 0)
    assert res.is_error()


def test_job_threading_and_counts(tmp_path):
    eb = DummyEventBus()
    s = AddOneStep("s", eb)
    task = Task("t", [s], eb)
    job = Job("j", [task], eb)
    res = job.execute(make_context(tmp_path), 3)
    assert not res.is_error()
    assert res.data == 4
    assert job.get_task_count() == 1
