import textwrap

from splurge_unittest_to_pytest import main


def _run_convert(src: str) -> str:
    res = main.convert_string(src)
    return getattr(res, "converted_code", res)


def test_typing_aliases_merge_and_preserve_aliases():
    src = textwrap.dedent(
        """
        # alias import form
        from typing import List as TList

        from typing import (
            Dict as TDict,
        )

        x: TList[int] = []
        y: TDict[str, int] = {}

        def test_sample():
            assert True
        """
    )

    out = _run_convert(src)

    # The converter should merge typing imports into a single ImportFrom
    # preserving aliases (as TList and TDict) and not losing alias names.
    assert "from typing import" in out
    assert "TList" in out
    assert "TDict" in out
