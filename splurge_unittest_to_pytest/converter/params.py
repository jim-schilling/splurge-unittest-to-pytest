"""Helpers to build fixture parameters for test methods.

This module provides small helpers used by stages that construct or
manipulate function parameter lists when converting TestCase methods into
pytest-style functions.
"""

import libcst as cst

DOMAINS = ["converter", "parameters"]

# Associated domains for this module


def get_fixture_param_names(setup_fixtures: dict[str, cst.FunctionDef]) -> list[str]:
    """Return fixture names from a mapping of fixtures (keys are names)."""
    return list(setup_fixtures.keys())


def make_fixture_params(fixture_names: list[str]) -> cst.Parameters:
    """Return a new ``libcst.Parameters`` containing fixture params.

    Args:
        fixture_names: Sequence of fixture parameter names to create.

    Returns:
        A ``libcst.Parameters`` instance containing one ``Param`` per name.
    """
    fixture_params: list[cst.Param] = [cst.Param(name=cst.Name(name)) for name in fixture_names]
    return cst.Parameters(params=fixture_params)


def append_fixture_params(existing_params: cst.Parameters, fixture_names: list[str]) -> cst.Parameters:
    """Return a new ``libcst.Parameters`` combining existing params with fixtures.

    Args:
        existing_params: The original ``libcst.Parameters`` to preserve.
        fixture_names: Iterable of fixture names to append as parameters.

    Returns:
        A new ``libcst.Parameters`` instance with the combined params.
    """
    existing = list(existing_params.params)
    fixture_params: list[cst.Param] = [cst.Param(name=cst.Name(n)) for n in fixture_names]
    return cst.Parameters(params=existing + fixture_params)
