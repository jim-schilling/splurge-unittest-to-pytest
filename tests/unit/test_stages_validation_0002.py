from types import SimpleNamespace

from splurge_unittest_to_pytest.stages.postvalidator import postvalidator_stage

DOMAINS = ["stages", "validation"]


def test_postvalidator_returns_error_for_invalid_code() -> None:
    bad = SimpleNamespace(code="def foo(\n")
    out = postvalidator_stage({"module": bad})
    assert "postvalidator_error" in out


def test_postvalidator_passes_through_non_string_code() -> None:
    obj = SimpleNamespace(code=None)
    out = postvalidator_stage({"module": obj})
    assert "postvalidator_error" not in out
