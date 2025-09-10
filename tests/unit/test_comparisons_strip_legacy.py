from pathlib import Path


def test_comparisons_have_no_legacy_section():
    comp_dir = Path("tmp") / "comparisons"
    assert comp_dir.exists(), "comparisons directory should exist"
    for p in comp_dir.glob("*.txt"):
        text = p.read_text(encoding="utf-8")
        assert "== LEGACY ==" not in text, f"File {p} still contains LEGACY section"
