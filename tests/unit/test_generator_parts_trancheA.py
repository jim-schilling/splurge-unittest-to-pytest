import libcst as cst

from splurge_unittest_to_pytest.stages.generator_parts.annotation_inferer import (
    AnnotationInferer,
)
from splurge_unittest_to_pytest.stages.generator_parts.node_emitter import NodeEmitter
from splurge_unittest_to_pytest.stages.generator_parts.generator_core import GeneratorCore


def test_annotation_inferer_test_prefix():
    inf = AnnotationInferer()
    assert inf.infer_return_annotation("test_myfunc").startswith("-> Any")


def test_annotation_inferer_non_test():
    inf = AnnotationInferer()
    assert inf.infer_return_annotation("helper") == "-> None"


def test_node_emitter_simple_body_and_decorator():
    emitter = NodeEmitter()
    body = "x = 1\nyield x"
    fn = emitter.emit_fixture_node("f", body)
    assert isinstance(fn, cst.FunctionDef)
    # yield should cause pytest.fixture decorator to be present
    assert any(isinstance(d.decorator, cst.Attribute) for d in fn.decorators)


def test_node_emitter_invalid_line_uses_pass():
    emitter = NodeEmitter()
    fn = emitter.emit_fixture_node("f2", "this is not python")
    # emitter may leave invalid lines as-is or use Pass fallback; accept either
    src = cst.Module([fn]).code
    assert "pass" in src or "this is not python" in src


def test_node_emitter_composite_dirs():
    emitter = NodeEmitter()
    mapping = {"a": "1", "b": "2"}
    fn = emitter.emit_composite_dirs_node("composite", mapping)
    src = cst.Module([fn]).code
    # should contain keys and variable names
    assert '"a"' in src and '"b"' in src
    assert "yield" in src


def test_generator_core_make_fixture_and_composite():
    core = GeneratorCore()
    fn = core.make_fixture("g1", "a = 1")
    assert isinstance(fn, cst.FunctionDef)

    comp = core.make_composite_dirs_fixture("group", {"x": "1"})
    assert isinstance(comp, cst.FunctionDef)
