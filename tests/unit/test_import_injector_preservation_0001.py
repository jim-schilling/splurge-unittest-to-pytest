import textwrap

from splurge_unittest_to_pytest import main


def _run_convert(src: str) -> str:
    """Run the converter on a string and return the converted source string.

    Note: main.convert_string returns a ConversionResult; return the
    converted_code field for ease of assertions in tests.
    """
    res = main.convert_string(src)
    # ConversionResult has .converted_code
    return getattr(res, "converted_code", res)


def test_typing_imports_preserve_comments_and_parentheses():
    src = textwrap.dedent(
        """
        # module header comment
        from typing import (
            List,  # list comment
        )

        from typing import Dict  # dict comment

            # use Dict so the typing import is required by the converter
            mymap: Dict[str, int] = {}

            def test_sample():
                assert True
        """
    )

    out = _run_convert(src)

    # The converter should merge typing imports into a single ImportFrom
    # preserving the parentheses form and collecting leading comments once.
    assert "from typing import (" in out
    assert "List" in out
    assert "Dict" in out
    # ensure comments are present and not duplicated
    assert "# list comment" in out
    assert out.count("# list comment") == 1


def test_import_injector_idempotent_when_rerun():
    src = textwrap.dedent(
        """
        import os

        def test_sample():
            assert True
        """
    )

    first = _run_convert(src)
    second = _run_convert(first)

    # Running the converter twice should not introduce duplicate imports
    assert first == second
