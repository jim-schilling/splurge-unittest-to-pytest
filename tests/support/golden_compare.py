from typing import Tuple

import libcst as cst


def _parse_module(code: str) -> cst.Module:
    """Parse code into a libcst.Module; fall back to wrapping if empty."""
    if not code or code.strip() == "":
        return cst.Module([])
    # strip common markdown fences that sometimes end up in golden files
    s = code or ""
    # remove any fence lines that start with ``` anywhere in the text
    parts = [ln for ln in s.splitlines() if not ln.strip().startswith("```")]
    s = "\n".join(parts).strip()
    if s == "":
        return cst.Module([])
    return cst.parse_module(s)


def normalize_module_code(code: str) -> str:
    """Return a canonical code text for a module by parsing and re-printing.

    This strips insignificant formatting differences while preserving structure.
    """
    mod = _parse_module(code)
    return mod.code


def assert_code_equal(actual: str, expected: str) -> Tuple[bool, str]:
    """Compare two code snippets by parsing and canonicalizing with libcst.

    Returns a tuple (equal, message) where message is empty when equal or
    contains a short diagnostic when not equal.
    """
    # Compare by libcst structural equality when possible
    a_mod = _parse_module(actual)
    e_mod = _parse_module(expected)
    try:
        if cst.Module.deep_equals(a_mod, e_mod):
            return True, ""
    except Exception:
        pass
    # Fall back to whitespace-normalized textual compare to tolerate blank-line
    # and formatting differences.
    import re

    a = re.sub(r"\s+", " ", a_mod.code).strip()
    e = re.sub(r"\s+", " ", e_mod.code).strip()
    if a == e:
        return True, ""
    return False, "Generated and expected code differ:\n--- actual ---\n{}\n--- expected ---\n{}\n".format(
        a_mod.code, e_mod.code
    )
