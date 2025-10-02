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


class ExceptionStep(Step):
    """Step that raises an exception during execution."""

    def execute(self, context: PipelineContext, input_data: int) -> Result[int]:
        raise RuntimeError("Test exception in step")


class WarningStep(Step):
    """Step that returns a warning result."""

    def execute(self, context: PipelineContext, input_data: int) -> Result[int]:
        return Result.warning(input_data + 1, ["Test warning"])


def test_step_execution_error_handling(tmp_path):
    """Test that step execution errors are properly caught and converted to Result.failure."""
    eb = DummyEventBus()
    step = ExceptionStep("failing_step", eb)
    context = make_context(tmp_path)

    # Test the run method which includes error handling
    result = step.run(context, 5)

    assert result.is_error()
    assert "Test exception in step" in str(result.error)
    assert result.metadata["step"] == "failing_step"
    assert result.metadata["context"] == context.run_id

    # Check that events were published (start and completion events)
    assert len(eb.published) >= 2


def test_task_with_failing_step(tmp_path):
    """Test task execution when a step fails."""
    eb = DummyEventBus()
    good_step = AddOneStep("good", eb)
    bad_step = ExceptionStep("bad", eb)

    task = Task("test_task", [good_step, bad_step], eb)
    context = make_context(tmp_path)

    result = task.execute(context, 10)

    assert result.is_error()
    assert "Test exception in step" in str(result.error)
    assert result.metadata["failed_step"] == "bad"
    assert result.metadata["step_index"] == 1


def test_task_with_warning_steps(tmp_path):
    """Test task execution with warning results."""
    eb = DummyEventBus()
    normal_step = AddOneStep("normal", eb)
    warning_step = WarningStep("warning", eb)
    final_step = AddOneStep("final", eb)

    task = Task("test_task", [normal_step, warning_step, final_step], eb)
    context = make_context(tmp_path)

    result = task.execute(context, 0)

    # Should complete with warnings (warning status, not success)
    assert result.status.value == "warning"
    assert result.data == 3  # 0 + 1 + 1 + 1
    assert len(result.warnings) == 1
    assert "Test warning" in result.warnings[0]


def test_job_with_failing_task(tmp_path):
    """Test job execution when a task fails."""
    eb = DummyEventBus()

    # Create a task that will fail
    bad_step = ExceptionStep("bad", eb)
    failing_task = Task("failing_task", [bad_step], eb)

    # Create a good task (won't be reached)
    good_step = AddOneStep("good", eb)
    good_task = Task("good_task", [good_step], eb)

    job = Job("test_job", [failing_task, good_task], eb)
    context = make_context(tmp_path)

    result = job.execute(context, 5)

    assert result.is_error()
    assert "Test exception in step" in str(result.error)
    assert result.metadata["job"] == "test_job"
    assert result.metadata["failed_task"] == "failing_task"
    assert result.metadata["task_index"] == 0


def test_job_with_warning_tasks(tmp_path):
    """Test job execution with tasks that produce warnings."""
    eb = DummyEventBus()

    # Task with warning
    warning_step = WarningStep("warning", eb)
    warning_task = Task("warning_task", [warning_step], eb)

    # Task with normal result
    normal_step = AddOneStep("normal", eb)
    normal_task = Task("normal_task", [normal_step], eb)

    job = Job("test_job", [warning_task, normal_task], eb)
    context = make_context(tmp_path)

    result = job.execute(context, 0)

    # Should complete with warnings (warning status, not success)
    assert result.status.value == "warning"
    assert result.data == 2  # Final result from last task
    assert len(result.warnings) == 1
    assert "Test warning" in result.warnings[0]


def test_task_with_none_data_warning_handling(tmp_path):
    """Test task handles warning results with None data correctly."""
    eb = DummyEventBus()

    class NoneDataWarningStep(Step):
        def execute(self, context: PipelineContext, input_data: int) -> Result[int]:
            return Result.warning(None, ["Warning with None data"])

    warning_step = NoneDataWarningStep("none_warning", eb)
    final_step = AddOneStep("final", eb)

    task = Task("test_task", [warning_step, final_step], eb)
    context = make_context(tmp_path)

    result = task.execute(context, 10)

    # Should complete with warning status and preserve data flow
    assert result.status.value == "warning"
    assert result.data == 11  # Data from final step
    assert len(result.warnings) == 1
