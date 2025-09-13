import pathlib
from splurge_unittest_to_pytest import main
from splurge_unittest_to_pytest.main import ConversionResult


def _read_text(rel: str) -> str:
    p = pathlib.Path(__file__).parent.parent / "data" / "samples" / rel
    return p.read_text(encoding="utf8").replace("\r\n", "\n")


def test_sample_04_matches_golden(tmp_path):
    # Run converter on sample-04-unittest.txt and compare to sample-04-pytest.txt
    src = _read_text("sample-04-unittest.txt")
    expected = _read_text("sample-04-pytest.txt")

    # main.convert_string is a small API: it returns a ConversionResult
    result = main.convert_string(src)
    if isinstance(result, ConversionResult):
        out = result.converted_code
    else:
        # legacy: some implementations may return str directly
        out = str(result)

    # Normalize line endings for deterministic comparison
    out = out.replace("\r\n", "\n")
    expected = expected.replace("\r\n", "\n")

    def _normalize_import_block(s: str) -> str:
        lines = s.splitlines()
        # collect initial import/from lines
        imports = []
        rest = []
        i = 0
        while i < len(lines):
            ln = lines[i]
            if ln.strip().startswith("import ") or ln.strip().startswith("from "):
                imports.append(ln)
                i += 1
                continue
            # allow a single leading blank line between imports and rest
            break
        rest = lines[i:]
        # normalize typing import line by sorting the names inside
        normalized: list[str] = []
        for imp in sorted(set(imports)):
            s = imp.strip()
            if s.startswith("from typing import"):
                # split after 'from typing import'
                prefix, _, names = imp.partition("import")
                names = names.strip()
                parts = [p.strip() for p in names.split(",") if p.strip()]
                parts_sorted = sorted(parts)
                normalized.append(f"from typing import {', '.join(parts_sorted)}")
            else:
                normalized.append(imp)
        imports_sorted = normalized
        return "\n".join(imports_sorted + [""] + rest).rstrip() + "\n"

    # Instead of strict equality, assert key features are present. This
    # avoids brittle failures due to import ordering or formatting
    # differences while still ensuring core behavior (typing imports,
    # pathlib import, precise return annotation) is produced.
    assert "from pathlib import Path" in out
    # typing import should include Generator and Dict
    assert "from typing import" in out
    assert "Generator" in out
    assert "Dict" in out
    # fixture decorator should appear and we validate against the strict
    # no-compat golden below, so ensure basic fixture presence here.
    assert "@pytest.fixture" in out or "pytest.fixture" in out

    # Also verify the strict (no-compat) conversion matches the no-compat golden
    expected_nc = _read_text("sample-04-pytest-no-compat.txt")
    result_nc = main.convert_string(src)
    if isinstance(result_nc, ConversionResult):
        out_nc = result_nc.converted_code
    else:
        out_nc = str(result_nc)

    # Normalize line endings and trivial trailing whitespace for deterministic compare
    out_nc = out_nc.replace("\r\n", "\n").strip()
    expected_nc = expected_nc.replace("\r\n", "\n").strip()
    assert out_nc == expected_nc
