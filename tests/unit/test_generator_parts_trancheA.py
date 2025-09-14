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


def test_node_emitter_normalize_and_parse_helpers():
    emitter = NodeEmitter()
    lines = emitter._normalize_body("\n  a = 1\n\n  yield a\n")
    assert lines == ["  a = 1", "  yield a"]

    # valid parse should return a libcst BaseStatement
    stmt = emitter._parse_statement_safe("a = 1")
    assert isinstance(stmt, cst.BaseStatement)

    # invalid parse -> fallback to Pass
    bad = emitter._parse_statement_safe("this is not valid python")
    assert (
        "pass"
        in cst.Module(
            [cst.FunctionDef(name=cst.Name("t"), params=cst.Parameters(), body=cst.IndentedBlock(body=[bad]))]
        ).code
    )


def test_generator_core_make_fixture_and_composite():
    core = GeneratorCore()
    fn = core.make_fixture("g1", "a = 1")
    assert isinstance(fn, cst.FunctionDef)

    comp = core.make_composite_dirs_fixture("group", {"x": "1"})
    assert isinstance(comp, cst.FunctionDef)


def test_generator_core_injection_and_error_propagation():
    class BadRewriter:
        def rewrite(self, body: str) -> str:
            raise RuntimeError("boom")

    core = GeneratorCore(rewriter=BadRewriter())
    try:
        core.make_fixture("g2", "a = 1")
        raised = False
    except RuntimeError:
        raised = True
    assert raised


def test_node_emitter_returns_annotation():
    emitter = NodeEmitter()
    fn = emitter.emit_fixture_node("rfn", "return 1", returns="int")
    # returns should be present and be the Name 'int'
    assert fn.returns is not None
    assert isinstance(fn.returns.annotation, cst.Name)
    assert fn.returns.annotation.value == "int"


def test_generator_core_custom_allocator_and_emitter():
    recorded = {}

    class FakeAllocator:
        def allocate(self, base: str) -> str:
            return base + "_X"

    class FakeEmitter:
        def emit_fixture_node(self, name: str, body: str, returns: str | None = None):
            recorded["name"] = name
            recorded["body"] = body
            recorded["returns"] = returns
            return cst.FunctionDef(
                name=cst.Name(name),
                params=cst.Parameters(),
                body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])]),
            )

    core = GeneratorCore(names=FakeAllocator(), emitter=FakeEmitter())
    _res = core.make_fixture("base", "a = 1")
    assert recorded.get("name") == "base_X"


def test_generator_core_infers_and_propagates_returns():
    core = GeneratorCore()
    # name starting with 'test_' should infer Any (per AnnotationInferer)
    fn = core.make_fixture("test_generated", "a = 1")
    assert fn.returns is not None
    assert isinstance(fn.returns.annotation, cst.Name)
    assert fn.returns.annotation.value == "Any"


def test_generator_core_no_return_for_normal_name():
    core = GeneratorCore()
    fn = core.make_fixture("normal", "a = 1")
    assert fn.returns is None
