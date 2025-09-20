import libcst as cst

from splurge_unittest_to_pytest.stages.generator_parts.namedtuple_bundler import bundle_named_locals


def test_bundle_named_locals_grouping():
    # create a fake class record with local_assignments mapping two locals to same Call
    call = cst.Call(func=cst.Name("make"), args=[cst.Arg(cst.Name("a"))])
    classrec = type("C", (), {})()
    classrec.local_assignments = {"foo": (call, None, set()), "bar": (call, None, set())}
    classrec.setup_assignments = {"foo": cst.Name("foo"), "bar": cst.Name("bar")}
    nodes, needs_typing, attr_map = bundle_named_locals({"TestX": classrec}, existing_top_names=set())
    # expect a classdef and a fixture function emitted
    # render via Module to get source code for nodes
    mod = cst.Module(body=list(nodes))
    code = mod.code
    assert "class _XData" in code or "class _TestXData" in code
    # attr_map should map foo/bar to a fixture name
    assert ("foo" in attr_map) or ("bar" in attr_map)
