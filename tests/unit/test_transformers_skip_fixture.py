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
