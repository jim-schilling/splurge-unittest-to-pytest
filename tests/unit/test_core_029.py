from splurge_unittest_to_pytest.stages.generator_parts import GeneratorCore
import libcst as cst

DOMAINS = ["core"]


def test_generator_core_make_fixture():
    gc = GeneratorCore()
    src = gc.make_fixture("my_fixture", "    return 1")
    # emitted node -> string for assertion
    code = cst.Module([src]).code if not isinstance(src, str) else str(src)
    assert "def my_fixture" in code
    # second allocation should receive a suffix
    src2 = gc.make_fixture("my_fixture", "    return 2")
    code2 = cst.Module([src2]).code if not isinstance(src2, str) else str(src2)
    assert "def my_fixture_2" in code2
