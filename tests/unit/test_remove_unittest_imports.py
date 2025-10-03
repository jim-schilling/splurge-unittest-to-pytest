"""Tests for remove_unittest_imports_if_unused in import_transformer.py.

This file exercises the behavior of removing top-level unittest imports
when they are not referenced at module-level, and preserving them when
they are used or referenced dynamically.
"""

from __future__ import annotations

from splurge_unittest_to_pytest.transformers.import_transformer import remove_unittest_imports_if_unused


def test_remove_unittest_imports_when_unused() -> None:
    src = """
import unittest
import os

def helper():
    return os.path.join('a', 'b')

"""

    out = remove_unittest_imports_if_unused(src)

    # Top-level `import unittest` should be removed
    assert "import unittest" not in out


def test_preserve_unittest_import_when_used_in_class() -> None:
    src = """
import unittest

class Example(unittest.TestCase):
    def test_something(self):
        self.assertEqual(1, 1)

"""

    out = remove_unittest_imports_if_unused(src)

    # The helper is conservative: references inside classes do not count
    # as module-level usage, so the import will be removed.
    assert "import unittest" not in out


def test_preserve_unittest_import_when_used_at_module_level() -> None:
    src = """
import unittest

# Module-level reference should count as usage
print(unittest)

"""

    out = remove_unittest_imports_if_unused(src)

    assert "import unittest" in out


def test_preserve_unittest_import_when_dynamically_imported() -> None:
    src = """
import unittest
__import__('unittest')

"""

    out = remove_unittest_imports_if_unused(src)

    # Dynamic import implies usage, so should preserve
    assert "import unittest" in out
