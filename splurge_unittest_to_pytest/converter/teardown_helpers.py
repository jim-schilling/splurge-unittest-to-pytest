"""Helpers for managing teardown cleanup mappings."""

from __future__ import annotations

from typing import Iterable

import libcst as cst


def associate_cleanup_with_fixtures(
    teardown_cleanup: dict[str, list[cst.BaseStatement]],
    fixture_names: Iterable[str],
    cleanup_statements: Iterable[cst.BaseStatement],
) -> None:
    """Associate cleanup_statements with the given fixture names inside teardown_cleanup."""
    cleanup_list = list(cleanup_statements)
    for fixture_name in fixture_names:
        if fixture_name not in teardown_cleanup:
            teardown_cleanup[fixture_name] = []
        teardown_cleanup[fixture_name].extend(list(cleanup_list))
