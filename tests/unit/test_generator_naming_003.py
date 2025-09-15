from splurge_unittest_to_pytest.stages.generator_parts.name_allocator import choose_local_name

DOMAINS = ["generator", "naming"]


def test_choose_local_name_simple():
    taken = set()
    name = choose_local_name("_x_value", taken)
    assert name == "_x_value"
    assert name in taken


def test_choose_local_name_suffixing():
    taken = {"_x_value", "_x_value_1", "_x_value_2"}
    name = choose_local_name("_x_value", taken)
    assert name == "_x_value_3"
    assert name in taken


def test_choose_local_name_is_deterministic():
    # repeated calls with same initial taken produce monotonic suffixing
    taken = {"_a", "_a_1"}
    n1 = choose_local_name("_a", taken)
    assert n1 == "_a_2"
    n2 = choose_local_name("_a", taken)
    assert n2 == "_a_3"
