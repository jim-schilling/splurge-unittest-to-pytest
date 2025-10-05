# Mypy overrides and the CLI module

This project enforces strict static typing across the core library modules using mypy. However, the CLI entrypoint (`splurge_unittest_to_pytest.cli`) uses Typer (Click) runtime helpers such as `OptionInfo` and dynamic callback objects that are difficult to express precisely without extensive runtime-only typing helpers.

To avoid noisy false-positives from the CLI while keeping the rest of the library strictly typed, we include a targeted mypy override in `pyproject.toml` that excludes the CLI module from strict checking.

Why the override exists
- Typer/Click uses runtime descriptors and callables to describe options which mypy cannot analyze accurately in many cases.
- Modeling every CLI option and callback precisely adds maintenance burden and distracts from library correctness.
- The CLI primarily performs argument parsing and delegates to well-typed library functions. We prefer to keep the library code strictly typed and test-driven.

How to re-enable strict checking for the CLI module
1. Open `pyproject.toml` and locate the `[tool.mypy.overrides]` (or equivalent) section.
2. Remove or adjust the override entry that targets `splurge_unittest_to_pytest.cli`.
3. Run `mypy splurge_unittest_to_pytest` and fix any new type errors. Common fixes include:
   - Adding narrow wrapper functions that convert Typer/Click runtime values to concrete types before passing to the library API.
   - Adding lightweight `typing.TypedDict` or `Protocol` types for OptionInfo callbacks used by the CLI.
   - Using `cast()` in the CLI boundary to convert runtime values to strongly-typed shapes before delegating.

Recommended approach if you want full static coverage
- Add minimal adapter functions in `splurge_unittest_to_pytest.cli` that coerce parsed CLI values into typed dataclasses (for example, `MigrationConfig`) before calling library functions.
- Keep adapters as small, well-tested units; they can use `# type: ignore` locally only where unavoidable.
- Prefer `cast()` and explicit conversions over broad `type: ignore` markers.

If you have questions or want help removing the override, open an issue or a PR and describe the desired strictness level — I can help implement the necessary wrappers and typing support.
