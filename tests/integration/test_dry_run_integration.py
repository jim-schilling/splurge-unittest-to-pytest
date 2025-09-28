import tempfile
from pathlib import Path

from splurge_unittest_to_pytest.context import MigrationConfig
from splurge_unittest_to_pytest.main import migrate


def test_dry_run_generates_code_without_unittest_import(tmp_path: Path):
    src = tmp_path / "sample_unittest.py"
    src.write_text(
        "import unittest\n\nclass T(unittest.TestCase):\n    def test_a(self):\n        self.assertTrue(True)\n",
        encoding="utf-8",
    )

    cfg = MigrationConfig(dry_run=True)
    res = migrate([str(src)], config=cfg)

    assert res.is_success()
    meta = getattr(res, "metadata", {}) or {}
    gen_map = meta.get("generated_code", {})
    # There should be exactly one generated output
    assert isinstance(gen_map, dict) and len(gen_map) == 1
    code = next(iter(gen_map.values()))

    # The converted code should not contain an unused 'import unittest'
    assert "import unittest" not in code
    # Should reference pytest or contain a converted test class/function
    assert "pytest" in code or "def test_" in code or "class Test" in code
