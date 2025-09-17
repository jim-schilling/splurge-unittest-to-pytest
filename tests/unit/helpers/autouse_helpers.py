"""Test-only helper utilities for autouse fixture injection used by tests.

These helpers re-use the internal fixture injector utilities so tests can
import a stable, test-only API at `tests.unit.helpers.autouse_helpers`.
"""

from __future__ import annotations

from typing import Iterable

import libcst as cst

from splurge_unittest_to_pytest.stages.fixture_injector import _find_insertion_index, _make_autouse_attach


def make_autouse_attach(setup_fixtures: dict | Iterable[str] | None) -> cst.FunctionDef:
    """Build a libcst.FunctionDef for an autouse fixture that attaches
    named fixtures onto request.instance.

    Accepts either a dict (keys are fixture names), an iterable of names,
    or None/empty to produce an empty attach fixture.
    """
    if setup_fixtures is None:
        names: list[str] = []
    elif isinstance(setup_fixtures, dict):
        names = list(setup_fixtures.keys())
    else:
        names = list(setup_fixtures)
    return _make_autouse_attach(names)


def insert_attach_fixture_into_module(module: cst.Module, func: cst.FunctionDef) -> cst.Module:
    """Insert the given FunctionDef into the module at the canonical
    insertion index (after imports/docstring).

    Returns a new Module instance with the function inserted.
    """
    insert_idx = _find_insertion_index(module)
    new_body = list(module.body)
    # Insert the function at the calculated index. Preserve existing nodes.
    new_body.insert(insert_idx, func)
    return module.with_changes(body=new_body)


__all__ = ["make_autouse_attach", "insert_attach_fixture_into_module"]
