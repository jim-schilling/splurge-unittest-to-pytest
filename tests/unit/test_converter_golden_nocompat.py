import pathlib
from splurge_unittest_to_pytest import main
from splurge_unittest_to_pytest.main import ConversionResult


def _read_text(rel: str) -> str:
    p = pathlib.Path(__file__).parent.parent / "data" / "samples" / rel
    return p.read_text(encoding="utf8").replace("\r\n", "\n")


def test_sample_04_matches_no_compat_golden():
    src = _read_text("sample-04-unittest.txt")
    expected = _read_text("sample-04-pytest-no-compat.txt")

    result = main.convert_string(src)
    if isinstance(result, ConversionResult):
        out = result.converted_code
    else:
        out = str(result)

    out = out.replace("\r\n", "\n").strip()
    expected = expected.replace("\r\n", "\n").strip()

    # Normalize runs of blank lines for comparison (allow minor spacing differences)
    def norm(s: str) -> str:
        import re

        s = s.replace("\r\n", "\n")
        s = "\n".join(line.rstrip() for line in s.splitlines())
        s = re.sub(r"\n{3,}", "\n\n", s)
        return s.strip()

    assert norm(out) == norm(expected)
