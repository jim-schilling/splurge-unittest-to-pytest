"""Tests for the public API of import_transformer.py.

Focus: cover the code path that inserts a ``re`` import when a transformer
indicates it is needed and provides an alias (e.g., ``import re as re2``).
"""

from __future__ import annotations

import pytest

from splurge_unittest_to_pytest.transformers.import_transformer import add_pytest_imports


class _StubTransformer:
    """Minimal transformer-like object used for testing add_pytest_imports."""

    def __init__(
        self, needs_re_import: bool = False, re_alias: str | None = None, re_search_name: str | None = None
    ) -> None:
        self.needs_re_import = needs_re_import
        self.re_alias = re_alias
        self.re_search_name = re_search_name


def test_add_pytest_imports_inserts_re_alias_and_pytest() -> None:
    """When a transformer requests a re import with an alias, ensure the
    returned source contains both an import for pytest and an aliased re
    import (covers the code path that constructs Import with AsName).
    """
    src = """
import os

def foo():
    return os.path.join("a", "b")

"""

    transformer = _StubTransformer(needs_re_import=True, re_alias="re2")

    out = add_pytest_imports(src, transformer=transformer)

    # Should have inserted pytest import
    assert "import pytest" in out

    # Should have inserted aliased re import
    assert "import re as re2" in out


@pytest.mark.parametrize(
    "src, transformer_kwargs, expect_pytest, expect_re",
    [
        # Early return when pytest already present in text
        ("import pytest\n\nprint('x')\n", {}, True, False),
        # Insert re without alias
        ("import os\n\n# placeholder\n", {"needs_re_import": True, "re_alias": None}, True, True),
        # Dynamic import of pytest should prevent insertion of pytest
        ("__import__('pytest')\n", {}, False, False),
        # Dynamic import of re prevents adding re even when transformer requests it
        ("__import__('re')\n", {"needs_re_import": True}, True, False),
        # importlib.import_module('pytest') should also be detected as dynamic import
        ("import importlib\nimportlib.import_module('pytest')\n", {}, False, False),
        # importlib.import_module('re') should also be detected and prevent adding re
        ("import importlib\nimportlib.import_module('re')\n", {"needs_re_import": True}, True, False),
        # aliasing importlib should still be detected (importlib as il; il.import_module('pytest'))
        ("import importlib as il\nil.import_module('pytest')\n", {}, False, False),
        ("import importlib as il\nil.import_module('re')\n", {"needs_re_import": True}, True, False),
    ],
)
def test_add_pytest_imports_various_branches(
    src: str, transformer_kwargs: dict, expect_pytest: bool, expect_re: bool
) -> None:
    """Parametrized cases covering several branches in add_pytest_imports.

    Cases:
    - Early string-level guard when pytest present
    - Insertion of re without alias
    - Dynamic import detection for pytest (prevents pytest insertion)
    - Dynamic import detection for re (prevents re insertion)
    """
    transformer = None
    if transformer_kwargs:
        transformer = _StubTransformer(**transformer_kwargs)

    out = add_pytest_imports(src, transformer=transformer)

    if expect_pytest:
        assert "import pytest" in out
    else:
        assert "import pytest" not in out

    if expect_re:
        # Accept either plain 'import re' or aliased 'import re as X'
        assert "import re" in out
    else:
        # Ensure no top-level 'import re' nor 'import re as' present
        assert "import re" not in out
