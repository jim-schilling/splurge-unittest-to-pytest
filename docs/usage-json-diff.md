# Using --json and --diff with splurge-unittest-to-pytest

This document shows how to use the new `--json` and `--diff` CLI flags added in Task‑3.1.

Overview

- `--json` (aka `--json_output`) emits newline-delimited JSON (NDJSON). Each line is a single JSON object describing a file processed during a dry-run. This is intended for tooling and CI consumption.
- `--diff` (aka `--show_diff`) controls whether unified diffs are included in the output. When combined with `--json` the diff is placed in the `summary.diff` field of the JSON record (raw unified-diff text). When used without `--json` the unified diff is printed to stdout in human-readable form.

Behavior

- Both flags are only meaningful in dry-run mode (`--dry-run` / `-n`). In non-dry-run runs the CLI will perform file writes and also print a human summary; JSON output is intended for diagnostics and tooling.
- `--json` produces NDJSON (one JSON object per line). This makes it streamable and easy to parse in pipelines. If you need a single JSON array, wrap the output or post-process it accordingly.

NDJSON schema (per-line)

Each line is a JSON object with the following shape:

- path: string — path to the input file
- changed: boolean — whether conversion would change the file
- errors: array — list of error messages (empty array when no errors)
- summary: object — small diagnostic summary
  - lines_original: integer
  - lines_converted: integer
  - lines_changed: integer
  - asserts_converted: integer
  - diff: (optional) string — unified diff text when `--diff` is requested and the file changed

Example outputs

1) NDJSON only (no diffs):

```text
{"path":"/tmp/test_file.py","changed":true,"errors":[],"summary":{"lines_original":10,"lines_converted":12,"lines_changed":2,"asserts_converted":3}}
```

2) NDJSON + diff (the `summary.diff` value contains the unified diff):

```text
{"path":"/tmp/test_file.py","changed":true,"errors":[],"summary":{"lines_original":10,"lines_converted":12,"lines_changed":2,"asserts_converted":3,"diff":"--- /tmp/test_file.py\n+++ /tmp/test_file.py (converted)\n@@ -1,3 +1,3 @@\n-    self.assertEqual(1, 1)\n+    assert 1 == 1\n"}}
```

3) Human-readable with --diff (no --json):

```text
Would convert: /tmp/test_file.py
Changes would be made:
    Lines changed: 10 -> 12
    Unittest assertions converted: 2
    Pytest assertions created: 2
--- /tmp/test_file.py
+++ /tmp/test_file.py (converted)
@@ -1,3 +1,3 @@
-    self.assertEqual(1, 1)
+    assert 1 == 1
```

Examples

Use the CLI as follows (dry-run):

```bash
python -m splurge_unittest_to_pytest.cli --dry-run --json path/to/tests
python -m splurge_unittest_to_pytest.cli --dry-run --json --diff path/to/tests
python -m splurge_unittest_to_pytest.cli --dry-run --diff path/to/tests  # human-readable diffs
```

Notes

- The `summary.diff` field contains raw unified-diff text. If you will store or transmit large diffs, consider truncating or encoding them.
- If you prefer a single JSON array instead of NDJSON, pipe the CLI output through a small wrapper that collects lines and wraps them in `[]`.

Feedback

If you'd like a different output format (JSON array, gzipped NDJSON, or a separate `--json-file` path), tell me and I can add it.