# Golden tests: adding, updating, and validating

This short note explains how the project handles "golden" (expected output) tests, the new AST-aware comparison helper, and the recommended workflow for adding or updating golden files.

Why this exists
- Golden tests historically compared generated output with exact text which is brittle to formatting-only changes and accidental copy/paste artifacts (for example Markdown fences). Tests now use an AST-aware comparator to reduce flakiness.

Where the code lives
- Helper: `tests/support/golden_compare.py`
- Golden files: `tests/data/goldens/*.expected`
- Integration tests: `tests/integration/*` (look for references to `.expected` files)

How the helper works (brief)
- Both actual (generated) and expected (.expected file) content are:
  1. stripped of accidental Markdown fence lines that start with ````` (so copy/paste from a README won't break parsing),
  2. parsed with `libcst.parse_module` into `libcst.Module` nodes,
  3. compared using `libcst.Module.deep_equals` (structural equality),
  4. if structural equality fails, it falls back to a whitespace-normalized textual comparison (collapses runs of whitespace) to tolerate blank-line/formatting differences.

Add or update a golden (recommended workflow)
1. Generate the output you want to pin as the golden. Typically this is done by running the small conversion pipeline used in the integration tests (examples below). Copy the `converted_code` (or `Module.code`) into a new `.expected` file under `tests/data/goldens/`.

2. If you are updating an existing golden because generator behavior changed intentionally, prefer to generate the canonical output using the pipeline and overwrite the golden so it continues to reflect the converter's canonical output.

3. Run the integration test(s) that reference the golden to validate:

```bash
# run just the integration tests in parallel
pytest -q tests/integration -n 9
```

4. If the test fails with a parse error pointing to `` ` `` characters, open the `.expected` file and remove accidental Markdown fences or extraneous content. The helper strips fence lines automatically, but large duplicated blocks or non-code artifacts should be removed manually.

Examples
- Typical minimal golden file:

```python
import os


def test_unix_feature():
    if not hasattr(os, 'getuid'):
        pytest.skip('os.getuid not available')
    assert isinstance(os.getuid(), int)
```

- Using the helper in a test module (already done in many integration tests):

```python
from pathlib import Path
from tests.support.golden_compare import assert_code_equal

converted = some_conversion_pipeline(input_text).converted_code
golden = Path("tests/data/goldens/my_golden.expected").read_text()
ok, msg = assert_code_equal(converted, golden)
assert ok, msg
```

Troubleshooting
- If a test still fails for a small formatting-only difference, accept the libcst canonical output as authoritative and update the golden by regenerating and writing the canonical `Module.code`.
- If a golden contains non-code artifacts (large README blocks, HTML comments, or duplicate code blocks), clean them manually before committing.

Notes
- The comparator intentionally prefers structural equality. Only use the textual fallback for small formatting differences — if real semantic differences exist, tests will fail and should be resolved by changing the converter or adjusting expectations.

If you want, I can add a small helper script under `tools/` that regenerates all goldens from `tests/data/samples` and writes them to `tests/data/goldens/` for easier bulk updates.
