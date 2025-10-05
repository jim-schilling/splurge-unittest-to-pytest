import pytest

from splurge_unittest_to_pytest.cli_adapters import build_config_from_cli
from splurge_unittest_to_pytest.context import MigrationConfig


class OptionStub:
    """Simple stand-in for Typer/Click OptionInfo-like objects.

    The adapter only needs a ``default`` attribute; we don't import Typer
    in tests so a small stub is sufficient to exercise the duck-typing.
    """

    def __init__(self, default):
        self.default = default


def test_basic_coercions_and_overrides():
    base = MigrationConfig()

    cli_kwargs = {
        "max_file_size_mb": OptionStub("20"),
        "dry_run": OptionStub(True),
        "file_patterns": OptionStub("a.py,b.py"),
        "assert_almost_equal_places": OptionStub("5"),
    }

    cfg = build_config_from_cli(base, cli_kwargs)

    assert isinstance(cfg, MigrationConfig)
    assert cfg.max_file_size_mb == 20
    assert cfg.dry_run is True
    assert cfg.file_patterns == ["a.py", "b.py"]
    assert cfg.assert_almost_equal_places == 5


@pytest.mark.parametrize(
    "input_value,expected",
    [
        ("x.py,y.py", ["x.py", "y.py"]),
        (["x.py", "y.py"], ["x.py", "y.py"]),
        (("x.py", "y.py"), ["x.py", "y.py"]),
        ({"x.py", "y.py"}, ["x.py", "y.py"]),
    ],
)
def test_file_patterns_variants(input_value, expected):
    base = MigrationConfig()
    cfg = build_config_from_cli(base, {"file_patterns": OptionStub(input_value)})
    # Order may change for sets; sort for comparison
    assert sorted(cfg.file_patterns) == sorted(expected)


def test_invalid_integer_raises_value_error():
    base = MigrationConfig()
    with pytest.raises(ValueError):
        build_config_from_cli(base, {"max_file_size_mb": OptionStub("not-an-int")})


def test_unknown_keys_are_ignored_and_none_skips_override():
    base = MigrationConfig(backup_root="original")

    cli_kwargs = {
        "nonexistent_key": OptionStub(1),
        "backup_root": OptionStub(None),
    }

    cfg = build_config_from_cli(base, cli_kwargs)

    # unknown key should be ignored and None should not override existing value
    assert cfg.backup_root == "original"
