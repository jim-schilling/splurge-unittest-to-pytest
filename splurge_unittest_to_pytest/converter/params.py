"""Helpers to build fixture parameters for test methods."""

import libcst as cst


def get_fixture_param_names(setup_fixtures: dict[str, cst.FunctionDef]) -> list[str]:
    """Return fixture names from a mapping of fixtures (keys are names)."""
    return list(setup_fixtures.keys())


def make_fixture_params(existing_params: cst.Parameters, fixture_names: list[str]) -> cst.Parameters:
    """Return a new Parameters object containing fixture params.

    The transformer uses this to append fixture parameters to test function
    signatures. For simplicity we construct Params containing only fixture
    params (the transformer already handles removing 'self' earlier).
    """
    fixture_params: list[cst.Param] = []
    for name in fixture_names:
        fixture_params.append(cst.Param(name=cst.Name(name)))

    return cst.Parameters(params=fixture_params)


def append_fixture_params(existing_params: cst.Parameters, fixture_names: list[str]) -> cst.Parameters:
    """Return a new Parameters object combining existing params with fixture params.

    This preserves existing params from `existing_params` and appends fixture
    params for each name in `fixture_names`.
    """
    existing = list(existing_params.params)
    fixture_params: list[cst.Param] = [cst.Param(name=cst.Name(n)) for n in fixture_names]
    return cst.Parameters(params=existing + fixture_params)
