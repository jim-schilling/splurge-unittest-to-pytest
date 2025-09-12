# Spec: Public API surface and cleanup

Date: 2025-09-12
Owner: Jim Schilling

This small spec documents the recommended public API exports for
`splurge_unittest_to_pytest` and a safe, reversible migration path for
internal refactors that may change import paths.

Goals
- Clearly list stable public functions/types in `__all__`.
- Avoid accidental breakage when moving internal helpers; provide
  compatibility shims where necessary.
- Document the recommended import paths for external users.

Public API (stable)
- `convert_file(path: str, ...) -> ConversionResult`
- `convert_string(src: str, ...) -> ConversionResult`
- `ConversionResult` dataclass
- Errors: `BackupError`, `ConversionError`, `EncodingError`,
  `FileNotFoundError`, `FileOperationError`, `ParseError`,
  `PermissionDeniedError`, `SplurgeError`

Recommendations
1. Keep `__all__` in `splurge_unittest_to_pytest/__init__.py` limited to the
   list above. Do not export internal helpers from `converter` or `stages`.
2. If an internal helper must be moved (for example `converter/helpers.py`),
   add a short compatibility shim in the old module that imports and re-exports
   the symbol, logging a deprecation comment in the docstring. Example:

   # In old module
   from .helpers import parse_method_patterns  # re-export (deprecated)

3. When landing refactors that move internal modules, update the README with
   a brief migration note and run the test-suite to catch import regressions.

Rollback
- Use small, single-purpose commits for each move and keep a compatibility
  shim for at least one release. When ready, remove the shim in a later
  minor release with a clear deprecation note.

Acceptance Criteria
- `__init__.py` lists only the stable API above.
- Internal moves include compatibility shims or documentation in `docs/`.
- Unit tests run successfully after changes.

---
Generated: 2025-09-12
