import libcst as cst

from splurge_unittest_to_pytest.stages.generator_parts.module_level_names import collect_module_level_names


def test_collect_module_level_names_assign_and_defs():
    mod = cst.parse_module(
        "\n".join(
            [
                "X = 1",
                "def foo():\n    pass",
                "class Bar:\n    pass",
            ]
        )
    )
    names = collect_module_level_names(mod)
    assert "X" in names
    assert "foo" in names
    assert "Bar" in names


def test_collect_module_level_names_imports_and_aliases():
    mod = cst.parse_module(
        "\n".join(
            [
                "import os",
                "import sys as system",
                "from math import sqrt, pi as PI",
            ]
        )
    )
    names = collect_module_level_names(mod)
    assert "os" in names
    assert "system" in names
    assert "sqrt" in names
    assert "PI" in names
