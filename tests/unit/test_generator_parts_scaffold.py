from splurge_unittest_to_pytest.stages.generator_parts import GeneratorCore


def test_generator_core_make_fixture():
    gc = GeneratorCore()
    src = gc.make_fixture("my_fixture", "    return 1")
    assert "def my_fixture" in src
    # second allocation should receive a suffix
    src2 = gc.make_fixture("my_fixture", "    return 2")
    assert "def my_fixture_2" in src2
