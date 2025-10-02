import libcst as cst

from splurge_unittest_to_pytest.transformers import fixture_transformer, skip_transformer


def mk_decorator_unittest_skip():
    call = cst.Call(
        func=cst.Attribute(value=cst.Name("unittest"), attr=cst.Name("skip")),
        args=[cst.Arg(value=cst.SimpleString('"reason"'))],
    )
    return cst.Decorator(decorator=call)


def mk_decorator_unittest_skipif():
    call = cst.Call(
        func=cst.Attribute(value=cst.Name("unittest"), attr=cst.Name("skipIf")),
        args=[cst.Arg(value=cst.Name("cond")), cst.Arg(value=cst.SimpleString('"r"'))],
    )
    return cst.Decorator(decorator=call)


def test_rewrite_skip_decorators():
    decorators = [mk_decorator_unittest_skip(), mk_decorator_unittest_skipif()]
    out = skip_transformer.rewrite_skip_decorators(decorators)
    # Should have transformed into pytest.mark.skip / pytest.mark.skipif calls
    assert out is not None
    assert any(isinstance(d.decorator, cst.Call) for d in out)


def mk_decorator_unittest_expected_failure_call():
    """Create @unittest.expectedFailure() decorator with arguments."""
    call = cst.Call(
        func=cst.Attribute(value=cst.Name("unittest"), attr=cst.Name("expectedFailure")),
        args=[cst.Arg(value=cst.SimpleString('"reason"'))],
    )
    return cst.Decorator(decorator=call)


def mk_decorator_unittest_expected_failure_attr():
    """Create @unittest.expectedFailure decorator without arguments."""
    attr = cst.Attribute(value=cst.Name("unittest"), attr=cst.Name("expectedFailure"))
    return cst.Decorator(decorator=attr)


def test_rewrite_skip_decorators_expected_failure_call():
    """Test rewrite_skip_decorators handles expectedFailure with arguments."""
    decorators = [mk_decorator_unittest_expected_failure_call()]
    out = skip_transformer.rewrite_skip_decorators(decorators)
    # Should transform into pytest.mark.xfail (covers lines 68-74)
    assert out is not None
    assert len(out) == 1
    assert isinstance(out[0].decorator, cst.Call)
    assert isinstance(out[0].decorator.func, cst.Attribute)
    assert out[0].decorator.func.attr.value == "xfail"


def test_rewrite_skip_decorators_expected_failure_attr():
    """Test rewrite_skip_decorators handles expectedFailure without arguments."""
    decorators = [mk_decorator_unittest_expected_failure_attr()]
    out = skip_transformer.rewrite_skip_decorators(decorators)
    # Should transform into pytest.mark.xfail
    assert out is not None
    assert len(out) == 1
    assert isinstance(out[0].decorator, cst.Call)
    assert isinstance(out[0].decorator.func, cst.Attribute)
    assert out[0].decorator.func.attr.value == "xfail"


def test_rewrite_skip_decorators_with_exception():
    """Test rewrite_skip_decorators handles exceptions gracefully."""
    # Create a decorator with an invalid structure that will cause an exception
    # This decorator has a Call but the func is not an Attribute, which should cause issues
    problematic_decorator = cst.Decorator(
        decorator=cst.Call(
            func=cst.Name("unittest"),  # This is not an Attribute, will cause issues
            args=[cst.Arg(value=cst.SimpleString('"reason"'))],
        )
    )

    decorators = [problematic_decorator]
    out = skip_transformer.rewrite_skip_decorators(decorators)
    # Should handle exception and return original decorators (covers lines 89-90)
    assert out is not None
    assert len(out) == 1
    assert out[0] is decorators[0]


def test_rewrite_skip_decorators_mixed():
    """Test rewrite_skip_decorators handles mixed known and unknown decorators."""
    decorators = [
        mk_decorator_unittest_skip(),
        cst.Decorator(decorator=cst.Name("unknown_decorator")),
        mk_decorator_unittest_expected_failure_attr(),
    ]
    out = skip_transformer.rewrite_skip_decorators(decorators)
    # Should transform known decorators and preserve unknown ones
    assert out is not None
    assert len(out) == 3
    # First should be transformed to pytest.mark.skip
    assert isinstance(out[0].decorator, cst.Call)
    assert out[0].decorator.func.attr.value == "skip"
    # Second should be preserved as-is
    assert out[1].decorator.value == "unknown_decorator"
    # Third should be transformed to pytest.mark.xfail
    assert isinstance(out[2].decorator, cst.Call)
    assert out[2].decorator.func.attr.value == "xfail"


def test_fixture_transform_string_based_simple():
    src = """
class T:
    def setUp(self):
        self.x = 1

    def tearDown(self):
        self.x = 0
"""
    out = fixture_transformer.transform_fixtures_string_based(src)
    assert "@pytest.fixture" in out


def test_create_class_fixture_minimal():
    node = fixture_transformer.create_class_fixture(["x=1"], ["x=0"])
    assert isinstance(node, cst.FunctionDef)
    assert node.name.value == "setup_class"


def test_create_instance_and_module_fixtures():
    inst = fixture_transformer.create_instance_fixture(["self.x=1"], ["self.x=0"])
    mod = fixture_transformer.create_module_fixture(["a=1"], ["a=0"])
    assert isinstance(inst, cst.FunctionDef)
    assert inst.name.value == "setup_method"
    assert isinstance(mod, cst.FunctionDef)
    assert mod.name.value == "setup_module"
