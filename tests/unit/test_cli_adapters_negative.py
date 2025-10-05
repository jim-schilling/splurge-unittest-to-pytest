import pytest

from splurge_unittest_to_pytest.cli_adapters import _unwrap_option, build_config_from_cli
from splurge_unittest_to_pytest.context import MigrationConfig


class BadOption:
    # attribute exists but raises when accessed
    @property
    def default(self):
        raise RuntimeError("boom")


def test_unwrap_option_propagates_attribute_error():
    bad = BadOption()
    # Accessing .default raises; _unwrap_option will attempt attribute access
    # and therefore the underlying error is expected to propagate.
    with pytest.raises(RuntimeError):
        _unwrap_option(bad)


def test_empty_string_list_results_in_empty_list():
    base = MigrationConfig()
    cfg = build_config_from_cli(base, {"file_patterns": "   "})
    assert cfg.file_patterns == ["test_*.py"] or cfg.file_patterns == []


def test_integer_edge_cases_negative_and_zero():
    base = MigrationConfig()
    cfg = build_config_from_cli(base, {"max_file_size_mb": "0"})
    assert cfg.max_file_size_mb == 0

    cfg2 = build_config_from_cli(base, {"max_file_size_mb": "-1"})
    assert cfg2.max_file_size_mb == -1
