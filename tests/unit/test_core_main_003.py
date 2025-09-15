import pathlib
import re
from splurge_unittest_to_pytest import main
from splurge_unittest_to_pytest.main import ConversionResult

DOMAINS = ["core", "main"]


SAMPLES = [
    "sample-01",
    "sample-02",
    "sample-04",
]


def _read(rel: str) -> str:
    p = pathlib.Path(__file__).parent.parent / "data" / "samples" / rel
    return p.read_text(encoding="utf8")


def _normalize_for_strict_compare(s: str) -> str:
    # Normalize line endings
    s = s.replace("\r\n", "\n")
    # strip trailing whitespace on each line
    s = "\n".join(line.rstrip() for line in s.splitlines())
    # collapse runs of more than 2 blank lines to exactly 2
    s = re.sub(r"\n{3,}", "\n\n", s)
    # normalize tempfile mkdtemp variants: Path(tempfile.mkdtemp()) vs tempfile.mkdtemp()
    s = s.replace("Path(tempfile.mkdtemp())", "<TMPDIR>")
    s = s.replace("tempfile.mkdtemp()", "<TMPDIR>")
    # strip leading/trailing common blank lines
    return s.strip() + "\n"


def _extract_and_normalize_imports(s: str) -> tuple[str, str, set[str]]:
    """Return (imports_block_normalized, rest_text, typing_names_set).

    imports_block_normalized is a deterministically-sorted import block (lines sorted).
    rest_text is the remaining code after removing the import block.
    typing_names_set is the set of names imported from typing (if any).
    """
    lines = s.splitlines()
    imports = []
    i = 0
    # Collect imports allowing blank lines interleaved; stop at first non-import, non-blank
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            # blank line: include as separator and continue
            i += 1
            continue
        if ln.strip().startswith("import ") or ln.strip().startswith("from "):
            imports.append(ln.rstrip())
            i += 1
            continue
        break
    rest = "\n".join(lines[i:]).lstrip()
    # sort imports deterministically
    # Normalize any 'from typing import ...' lines to canonical sorted name lists
    norm_imports: list[str] = []
    for imp in sorted(set(imports)):
        s_imp = imp.strip()
        if s_imp.startswith("from typing import"):
            _, _, names = s_imp.partition("import")
            parts = [p.strip() for p in names.split(",") if p.strip()]
            parts_sorted = sorted(parts)
            norm_imports.append(f"from typing import {', '.join(parts_sorted)}")
        else:
            norm_imports.append(imp)
    imports_sorted = norm_imports
    # extract typing import names
    typing_names = set()
    for imp in imports_sorted:
        s_imp = imp.strip()
        if s_imp.startswith("from typing import"):
            _, _, names = s_imp.partition("import")
            for p in names.split(","):
                n = p.strip()
                if n:
                    typing_names.add(n)
    imports_norm = "\n".join(imports_sorted) + "\n\n" if imports_sorted else ""
    return imports_norm, rest, typing_names


def test_samples_match_goldens_strict():
    for base in SAMPLES:
        src = _read(f"{base}-unittest.txt")
        expected = _read(f"{base}-pytest.txt")
        result = main.convert_string(src)
        if isinstance(result, ConversionResult):
            out = result.converted_code
        else:
            out = str(result)

    norm_out = _normalize_for_strict_compare(out)
    norm_expected = _normalize_for_strict_compare(expected)

    out_imports, out_rest, out_typing = _extract_and_normalize_imports(norm_out)
    exp_imports, exp_rest, exp_typing = _extract_and_normalize_imports(norm_expected)

    # imports block should be the same modulo ordering; compare as sets
    assert set(out_imports.splitlines()) == set(exp_imports.splitlines()), (
        f"Import block mismatch for {base}\nOUT:\n{out_imports}\nEXP:\n{exp_imports}"
    )

    # typing imports names should match as sets
    assert out_typing == exp_typing, f"Typing import names mismatch for {base}: {out_typing} != {exp_typing}"

    # the remainder must match modulo minor whitespace/blank-line differences
    # collapse runs of whitespace inside lines to single spaces for comparison
    def collapse_whitespace(s: str) -> str:
        return re.sub(r"\s+", " ", s).strip()

    assert collapse_whitespace(out_rest) == collapse_whitespace(exp_rest), f"Body mismatch for {base}"
