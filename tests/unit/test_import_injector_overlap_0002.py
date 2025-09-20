import re
import textwrap

from splurge_unittest_to_pytest import main


def _run_convert(src: str) -> str:
    res = main.convert_string(src)
    return getattr(res, "converted_code", res)


def test_typing_not_requested_if_user_defines_name():
    src = textwrap.dedent(
        """
        # user defines a top-level name 'List' which should prevent
        # the converter from inserting 'List' from typing.

        class List:
            pass

        def test_sample():
            # no typing.List is used; the converter must not insert
            # `from typing import List` when a top-level List exists.
            assert True
        """
    )

    out = _run_convert(src)

    # Ensure we don't add a typing import for 'List' when user defines it.
    # Avoid matching the phrase if it appears inside a comment. Match only
    # a real import statement at the start of a line.
    assert not re.search(r"(?m)^[ \t]*from\s+typing\s+import\s+List\b", out)
