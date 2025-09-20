from types import SimpleNamespace

import libcst as cst

from splurge_unittest_to_pytest.stages.postvalidator import postvalidator_stage


def test_postvalidator_accepts_valid_module() -> None:
    src = "import pytest\n\nclass A:\n    pass\n"
    module = cst.parse_module(src)
    res = postvalidator_stage({"module": module})
    assert "postvalidator_error" not in res


def test_postvalidator_detects_syntax_error() -> None:
    class M:
        code = "def f(:\n"

    res = postvalidator_stage({"module": M()})
    assert "postvalidator_error" in res


def test_postvalidator_returns_error_for_invalid_code() -> None:
    bad = SimpleNamespace(code="def foo(\n")
    out = postvalidator_stage({"module": bad})
    assert "postvalidator_error" in out


def test_postvalidator_passes_through_non_string_code() -> None:
    obj = SimpleNamespace(code=None)
    out = postvalidator_stage({"module": obj})
    assert "postvalidator_error" not in out
