from pathlib import Path


def _run_checks() -> int:
    files = [
        Path("tests/data/generated_from_bak/test_cli.py.py"),
        Path("tests/data/generated_from_bak/test_init_api.py.py"),
    ]

    ok = True
    for p in files:
        print("Checking", p)
        if not p.exists():
            print("  MISSING")
            ok = False
            continue
        src = p.read_text(encoding="utf-8")
        try:
            compile(src, str(p), "exec")
            print("  OK: syntactically valid")
        except Exception as e:
            print("  ERROR:", type(e).__name__, e)
            ok = False

    if not ok:
        return 2
    print("All checks passed")
    return 0


def main(*, argv: list[str] | None = None) -> int:
    return _run_checks()


if __name__ == "__main__":
    raise SystemExit(main(argv=None))
