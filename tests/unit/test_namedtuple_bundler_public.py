import libcst as cst

from splurge_unittest_to_pytest.stages.generator_parts.namedtuple_bundler import bundle_named_locals


def test_bundle_named_locals_empty_out():
    nodes, typing, mapping = bundle_named_locals({}, set())
    assert isinstance(nodes, list)
    assert isinstance(typing, set)
    assert isinstance(mapping, dict)


def test_bundle_named_locals_grouping_simple():
    # create a fake class descriptor with two local assignments originating
    # from the same Call so bundling will consider them
    call = cst.parse_expression("make()")
    class_obj = type("C", (), {})()
    class_obj.local_assignments = {"a": (call, None, set()), "b": (call, None, set())}
    class_obj.setup_assignments = {"a": cst.Name("a"), "b": cst.Name("b")}
    out = {"TestX": class_obj}
    nodes, typing, mapping = bundle_named_locals(out, set())
    # nodes should include class + fixture function for the bundling
    assert isinstance(nodes, list)
    # mapping should contain attributes mapped to a fixture name
    assert mapping
