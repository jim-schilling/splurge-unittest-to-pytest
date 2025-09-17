from pathlib import Path

from tools.rename_tests_by_domains import build_proposals


def test_renamer_skips_helpers_and_non_test_files(tmp_path: Path) -> None:
    # create structure
    root = tmp_path / "tests"
    helpers = root / "unit" / "helpers"
    helpers.mkdir(parents=True)
    tests_dir = root / "unit"
    # file inside helpers should be ignored
    h = helpers / "autouse_helpers.py"
    h.write_text("DOMAINS = ['core']\n")
    # non-test file at top-level should be ignored
    conf = tests_dir / "conftest.py"
    conf.write_text("DOMAINS = ['misc']\n")
    # a real test file should be picked up
    real = tests_dir / "test_example.py"
    real.write_text("DOMAINS = ['core']\n")

    proposals = build_proposals(root)
    # only the real test should be proposed
    names = [p.name for _, p in proposals]
    assert any("test_core" in n for n in names)
    assert not any("autouse_helpers" in n for n in names)
    assert not any("conftest" in n for n in names)
