import pytest
import typer

from splurge_unittest_to_pytest import cli as cli_module
from splurge_unittest_to_pytest.context import MigrationConfig
from splurge_unittest_to_pytest.result import Result


def _make_success_with_generated(files_and_code: dict):
    # Return a Result.success with metadata containing generated_code mapping
    res = Result.success([*files_and_code.keys()])
    res.metadata["generated_code"] = files_and_code
    return res


def test_migrate_dry_run_list_files_and_diff(monkeypatch, tmp_path, capsys):
    # Setup: validate returns some files
    monkeypatch.setattr(
        cli_module, "validate_source_files_with_patterns", lambda s, r, p, rec: [str(tmp_path / "a.py")]
    )

    # Context load returns default config
    monkeypatch.setattr(
        cli_module.ContextManager, "load_config_from_file", staticmethod(lambda p: Result.success(MigrationConfig()))
    )

    # Event bus
    from splurge_unittest_to_pytest.events import EventBus

    monkeypatch.setattr(cli_module, "create_event_bus", lambda: EventBus())

    # Make main.migrate return generated_code mapping
    fake_code = {str(tmp_path / "a.py"): 'print("hello")\n'}
    monkeypatch.setattr(
        cli_module.main_module,
        "migrate",
        lambda files, config=None, event_bus=None: _make_success_with_generated(fake_code),
    )

    # Run with list_files mode
    cli_module.migrate(
        [str(tmp_path)],
        config_file=None,
        dry_run=True,
        list_files=True,
        info=False,
        debug=False,
        show_suggestions=False,
        use_case_analysis=False,
        generate_field_help=None,
        list_templates=False,
        use_template=None,
        generate_docs=None,
    )
    out = capsys.readouterr().out
    assert "== FILES:" in out

    # Run with diff mode (should print DIFF header and unified diff lines)
    cli_module.migrate(
        [str(tmp_path)],
        config_file=None,
        dry_run=True,
        diff=True,
        list_files=False,
        info=False,
        debug=False,
        show_suggestions=False,
        use_case_analysis=False,
        generate_field_help=None,
        list_templates=False,
        use_template=None,
        generate_docs=None,
    )
    out2 = capsys.readouterr().out
    assert "== DIFF:" in out2 or "== PYTEST:" in out2


def test_migrate_main_failure_propagates(monkeypatch):
    monkeypatch.setattr(cli_module, "validate_source_files_with_patterns", lambda s, r, p, rec: ["x.py"])
    monkeypatch.setattr(
        cli_module.ContextManager, "load_config_from_file", staticmethod(lambda p: Result.success(MigrationConfig()))
    )
    from splurge_unittest_to_pytest.events import EventBus

    monkeypatch.setattr(cli_module, "create_event_bus", lambda: EventBus())

    monkeypatch.setattr(
        cli_module.main_module,
        "migrate",
        lambda files, config=None, event_bus=None: Result.failure(RuntimeError("boom")),
    )

    with pytest.raises(typer.Exit):
        cli_module.migrate(["x"], config_file=None, info=False, debug=False)


def test_config_validation_advisor_and_templates():
    # Suggestion when large file size
    from splurge_unittest_to_pytest.config_validation import (
        ValidatedMigrationConfig,
        generate_config_from_template,
        generate_configuration_suggestions,
        get_template,
        list_available_templates,
    )

    vm = ValidatedMigrationConfig(**{"file_patterns": ["test_*.py"]})
    suggestions = generate_configuration_suggestions(vm)
    assert isinstance(suggestions, list)

    # Template manager
    names = list_available_templates()
    assert isinstance(names, list)
    if names:
        t = get_template(names[0])
        assert t is not None
        d = generate_config_from_template(names[0])
        assert isinstance(d, dict)
    with pytest.raises(ValueError):
        generate_config_from_template("no-such-template-xyz")


def test_pipeline_failure_and_events(monkeypatch):
    from splurge_unittest_to_pytest.events import EventBus, JobCompletedEvent, PipelineCompletedEvent
    from splurge_unittest_to_pytest.pipeline import PipelineFactory, Step
    from splurge_unittest_to_pytest.result import Result

    bus = EventBus()
    factory = PipelineFactory(bus)

    class BadStep(Step):
        def execute(self, context, input_data):
            return Result.failure(RuntimeError("step fail"))

    step = BadStep("bad", bus)
    task = factory.create_task("t", [step])
    job = factory.create_job("j", [task])
    pipeline = factory.create_pipeline("p", [job])

    events = []
    bus.subscribe(JobCompletedEvent, lambda e: events.append(("job", e)))
    bus.subscribe(PipelineCompletedEvent, lambda e: events.append(("pipeline", e)))

    class Ctx:
        run_id = "r2"

    r = pipeline.execute(Ctx(), initial_input=None)
    assert r.is_error()
    # Events should include job and pipeline completed with failure
    kinds = {k for k, _ in events}
    assert "job" in kinds and "pipeline" in kinds


def test_transform_assert_raises_ast():
    import libcst as cst

    from splurge_unittest_to_pytest.transformers.assert_transformer import transform_assert_raises

    # Build a call like: self.assertRaises(ValueError, foo)
    call = cst.Call(
        func=cst.Attribute(value=cst.Name("self"), attr=cst.Name("assertRaises")),
        args=[cst.Arg(value=cst.Name("ValueError")), cst.Arg(value=cst.Name("foo"))],
    )
    out = transform_assert_raises(call)
    # Should produce a Call whose func is pytest.raises
    assert isinstance(out, cst.Call)
    assert isinstance(out.func, cst.Attribute)
    assert getattr(out.func.attr, "value", "") == "raises"
