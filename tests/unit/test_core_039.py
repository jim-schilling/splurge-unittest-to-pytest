import libcst as cst

from splurge_unittest_to_pytest.stages import generator_parts
from splurge_unittest_to_pytest import print_diagnostics

DOMAINS = ["core"]


def test_node_emitter_emit_fixture_node_basic():
    emitter = generator_parts.node_emitter.NodeEmitter()
    fn = emitter.emit_fixture_node("my_fixture", "return 1")
    # basic shape assertions
    assert isinstance(fn, cst.FunctionDef)
    assert fn.name.value == "my_fixture"
    # body should contain a SimpleStatementLine
    assert any(isinstance(s, cst.SimpleStatementLine) for s in fn.body.body)


def test_node_emitter_emit_composite_dirs_node():
    emitter = generator_parts.node_emitter.NodeEmitter()
    mapping = {"a": "1", "b": "2"}
    fn = emitter.emit_composite_dirs_node("composite", mapping)
    assert isinstance(fn, cst.FunctionDef)
    assert fn.name.value == "composite"
    # should contain assignments for mapping values
    src = cst.Module([]).code + "\n" + cst.Module([fn]).code
    assert "a" in src and "b" in src


def test_generator_core_make_fixture_basic():
    core = generator_parts.generator_core.GeneratorCore()
    fn = core.make_fixture("f1", "a = 1")
    assert isinstance(fn, cst.FunctionDef)
    assert fn.name.value == "f1"


def test_print_diagnostics_find_and_print(tmp_path, capsys):
    # Create a fake diagnostics run directory structure
    root = tmp_path / "diagnostics_root"
    run = root / "splurge-diagnostics-0001"
    run.mkdir(parents=True)
    # create marker file expected by print_diagnostics (it globs "splurge-diagnostics-*")
    marker = run / "splurge-diagnostics-marker.txt"
    marker.write_text("marker")
    # pass the parent root (which contains the run directories)
    found = print_diagnostics.find_diagnostics_root(cli_root=str(root))
    assert found is not None

    recent = print_diagnostics.find_most_recent_run(found)
    assert recent is not None

    # call print_run_info which prints to stdout
    print_diagnostics.print_run_info(recent)
    captured = capsys.readouterr()
    # output includes the marker filename and its contents
    assert "splurge-diagnostics-marker.txt" in captured.out or "marker" in captured.out
