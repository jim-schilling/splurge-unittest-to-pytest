"""Associate teardown cleanup statements with fixtures.

Helpers in this module record mappings from fixture names to lists of
cleanup statement nodes to execute when a fixture is torn down. The
primary function mutates a provided mapping in-place to append cleanup
statements for one or more fixture names.

Publics:
    associate_cleanup_with_fixtures

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from __future__ import annotations

from typing import Iterable

import libcst as cst

DOMAINS = ["converter", "teardown"]

# Associated domains for this module
# Moved to top of module after imports.


def associate_cleanup_with_fixtures(
    teardown_cleanup: dict[str, list[cst.BaseStatement]],
    fixture_names: Iterable[str],
    cleanup_statements: Iterable[cst.BaseStatement],
) -> None:
    """Associate cleanup statements with fixture names.

    Args:
        teardown_cleanup: Mapping from fixture name to a list of cleanup
            statement nodes. This mapping will be mutated in-place.
        fixture_names: Iterable of fixture names to associate the cleanup with.
        cleanup_statements: Iterable of :class:`libcst.BaseStatement` nodes
            representing cleanup operations to append.
    """

    cleanup_list = list(cleanup_statements)
    for fixture_name in fixture_names:
        if fixture_name not in teardown_cleanup:
            teardown_cleanup[fixture_name] = []
        teardown_cleanup[fixture_name].extend(list(cleanup_list))
