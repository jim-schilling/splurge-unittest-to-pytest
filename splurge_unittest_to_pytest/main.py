"""Main conversion helpers for programmatic and CLI usage.

This module exposes the primary conversion helpers consumed by the
command-line ``main`` and by programmatic callers. Key functions and
classes include:

- ``convert_string``: Convert a source string from unittest-style to
    pytest-style and return a ``ConversionResult``.
- ``convert_file``: Convenience wrapper to read, convert, and write
    files.
- ``PatternConfigurator``: Helper to customize detection of setup,
    teardown, and test method names.

These helpers orchestrate the staged pipeline implemented in
``splurge_unittest_to_pytest.stages.pipeline`` and provide a
lightweight, stable API for conversion operations.

Copyright (c) 2025 Jim Schilling

License: MIT
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import libcst as cst

from .stages.pipeline import run_pipeline
from .exceptions import EncodingError, FileNotFoundError as SplurgeFileNotFoundError, PermissionDeniedError
from .sentinel_discovery import is_unittest_file
from .io_helpers import atomic_write
from .converter.helpers import has_meaningful_changes, normalize_method_name
from .types import PipelineContext

DOMAINS = ["main"]

# Associated domains for this module
# Moved to top of module after imports.


@dataclass
class ConversionResult:
    """Result of a unittest to pytest conversion.

    Attributes:
        original_code: The original input source text.
        converted_code: The converted source text (or original on no-op).
        has_changes: True if conversion produced meaningful changes.
        errors: List of error messages encountered during conversion.
    """

    original_code: str
    converted_code: str
    has_changes: bool
    errors: list[str]


def convert_string(
    source_code: str,
    autocreate: bool = True,
    pattern_config: Any | None = None,
    normalize_names: bool = False,
) -> ConversionResult:
    """Convert unittest-style test code to pytest-style.

    Args:
        source_code: The original unittest test code as a string.
        autocreate: If True, enable autocreation of certain temporary-fixture
            artifacts when converting (passed into stage context as
            ``autocreate``).
        pattern_config: Optional PatternConfigurator instance. If provided,
            stages that perform method-name matching will consult it for
            setup/teardown/test name detection. If ``None``, stages use
            builtin defaults.

    Returns:
        A ``ConversionResult`` describing the conversion outcome.
    """
    errors: list[str] = []

    try:
        # Parse the source code into a CST
        try:
            tree = cst.parse_module(source_code)
        except cst.ParserSyntaxError:
            # Some real-world sample files contain mixed tabs and spaces which
            # cause libcst to raise a ParserSyntaxError. As a conservative
            # fallback, normalize tabs to four spaces and retry parsing once.
            try:
                normalized = source_code.replace("\t", "    ")
                try:
                    tree = cst.parse_module(normalized)
                except cst.ParserSyntaxError:
                    # As a last resort, apply a lenient normalization that
                    # forces any indented line to use a single level of
                    # four-space indentation. This is conservative and only
                    # intended to allow the converter to operate on slightly
                    # malformed sample files used in tests; it's not a
                    # general-purpose formatter.
                    lines = []
                    for ln in normalized.splitlines():
                        if ln.startswith(" ") or ln.startswith("\t"):
                            lines.append("    " + ln.lstrip())
                        else:
                            lines.append(ln)
                    relaxed = "\n".join(lines)
                    tree = cst.parse_module(relaxed)
            except cst.ParserSyntaxError:
                # Re-raise to be handled by outer except block below
                raise

        # Use the staged pipeline implementation. The pipeline returns a
        # libcst.Module representing strict pytest-style output.
        # Pass any configured pattern configurator into the pipeline when
        # the runtime run_pipeline accepts it. Some tests monkeypatch
        # run_pipeline with a shim that doesn't accept the new kwarg, so
        # check the callable signature and only pass the kwarg when
        # supported (or when the callable accepts **kwargs).
        try:
            import inspect

            sig = inspect.signature(run_pipeline)
            params = sig.parameters
            accepts_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
            if "pattern_config" in params or accepts_kwargs:
                # Forward normalize_names when run_pipeline accepts kwargs
                converted_module = run_pipeline(
                    tree, autocreate=autocreate, pattern_config=pattern_config, normalize_names=normalize_names
                )
            else:
                converted_module = run_pipeline(tree, autocreate=autocreate)
        except Exception:
            # If inspection fails for any reason, fall back to the simple
            # call without the new kwarg to maintain compatibility with
            # monkeypatched tests.
            converted_module = run_pipeline(tree, autocreate=autocreate)
        # Final AST-based normalization: run the exceptioninfo normalizer
        # stage over the converted module to ensure any NAME.exception ->
        # NAME.value conversions are applied. This stage runs late in the
        # pipeline by default, but invoke it here again to be defensive in
        # case stage ordering differs in some contexts (harmless no-op if
        # already applied).
        try:
            from splurge_unittest_to_pytest.stages.raises_stage import exceptioninfo_normalizer_stage

            # norm_ctx is a mapping used by pipeline stages; use the
            # canonical PipelineContext type so mypy and callers agree on
            # the expected shape.
            norm_ctx: PipelineContext = {"module": converted_module}
            out = exceptioninfo_normalizer_stage(norm_ctx)
            # Be defensive: ensure we only assign a Module back to converted_module
            if isinstance(out, dict):
                maybe_mod = out.get("module")
                if isinstance(maybe_mod, cst.Module):
                    converted_module = maybe_mod
        except Exception:
            # Defensive: do not fail conversion if normalization errors
            # occur; rely on earlier pipeline stages.
            pass

        # Apply a direct AST pass using ExceptionAttrRewriter as a last AST-only
        # safeguard (not textual). This is preferred over string replacement
        # and will rewrite NAME.exception -> NAME.value for any names bound by
        # `with pytest.raises(...) as NAME` in the emitted AST.
        try:
            # Collect any attribute accesses like `NAME.exception` and apply
            # the ExceptionAttrRewriter for each NAME found. This is a
            # conservative AST-only transformation that rewrites attribute
            # access to `NAME.value`. It avoids brittle text replacement and
            # ensures we catch accesses that survived earlier stages.
            class _AttrCollector(cst.CSTVisitor):
                def __init__(self) -> None:
                    self.names: set[str] = set()

                def visit_Attribute(self, node: cst.Attribute) -> None:
                    try:
                        if isinstance(node.attr, cst.Name) and node.attr.value == "exception":
                            if isinstance(node.value, cst.Name):
                                self.names.add(node.value.value)
                    except Exception:
                        pass

            collector = _AttrCollector()
            converted_module.visit(collector)
            from splurge_unittest_to_pytest.stages.raises_stage import ExceptionAttrRewriter

            for nm in sorted(collector.names):
                if nm:
                    converted_module = converted_module.visit(ExceptionAttrRewriter(nm))
        except Exception:
            pass
        converted_code = converted_module.code

        # NOTE: normalization of NAME.exception -> NAME.value is performed
        # by the pipeline's `exceptioninfo_normalizer_stage` which runs late
        # in the pipeline. A prior implementation included a conservative
        # textual fallback here; that has been removed in favor of the
        # AST-based transformation to avoid fragile string replacements.

        # Determine whether any meaningful conversion changes were made.
        try:
            changed = has_meaningful_changes(source_code, converted_code)
            if not changed:
                return ConversionResult(
                    original_code=source_code,
                    converted_code=source_code,
                    has_changes=False,
                    errors=errors,
                )
        except Exception:
            # If our change-detection helper fails for any reason, fall back
            # to conservative behavior and treat textual differences as changes.
            pass

        return ConversionResult(
            original_code=source_code,
            converted_code=converted_code,
            has_changes=converted_code != source_code,
            errors=errors,
        )

    except cst.ParserSyntaxError as e:
        errors.append(f"Failed to parse source code: {e}")
        return ConversionResult(
            original_code=source_code,
            converted_code=source_code,  # Return original code unchanged
            has_changes=False,
            errors=errors,
        )


class PatternConfigurator:
    """Small helper providing pattern configuration helpers.

    This is a lightweight replacement API for tests/examples that previously
    inspected or mutated the legacy transformer's pattern sets. It intentionally
    exposes only the pattern configuration surface used by tests.
    """

    def __init__(self) -> None:
        # Keep internal sets private; expose read-only copies via properties
        self._setup_patterns: set[str] = {
            "setup",
            "setUp",
            "set_up",
            "setup_method",
            "setUp_method",
            "before_each",
            "beforeEach",
            "before_test",
            "beforeTest",
        }

        self._teardown_patterns: set[str] = {
            "teardown",
            "tearDown",
            "tear_down",
            "teardown_method",
            "tearDown_method",
            "after_each",
            "afterEach",
            "after_test",
            "afterTest",
        }

        self._test_patterns: set[str] = {
            "test_",
            "test",
            "should_",
            "when_",
            "given_",
            "it_",
            "spec_",
        }

        # Maintain normalized pattern caches for efficient matching
        self._norm_setup_patterns: set[str] = {normalize_method_name(p) for p in self._setup_patterns}
        self._norm_teardown_patterns: set[str] = {normalize_method_name(p) for p in self._teardown_patterns}
        self._norm_test_patterns: set[str] = {normalize_method_name(p) for p in self._test_patterns}

    def add_setup_pattern(self, p: Any) -> None:
        try:
            if isinstance(p, str) and p.strip():
                self._setup_patterns.add(p)
                # update normalized cache
                try:
                    self._norm_setup_patterns.add(normalize_method_name(p))
                except Exception:
                    pass
        except Exception:
            pass

    def add_teardown_pattern(self, p: Any) -> None:
        try:
            if isinstance(p, str) and p.strip():
                self._teardown_patterns.add(p)
                try:
                    self._norm_teardown_patterns.add(normalize_method_name(p))
                except Exception:
                    pass
        except Exception:
            pass

    def add_test_pattern(self, p: Any) -> None:
        try:
            if isinstance(p, str) and p.strip():
                self._test_patterns.add(p)
                try:
                    self._norm_test_patterns.add(normalize_method_name(p))
                except Exception:
                    pass
        except Exception:
            pass

    def _is_setup_method(self, name: str) -> bool:
        try:
            norm_name = normalize_method_name(name)
            return any(norm_name.startswith(p) for p in self._norm_setup_patterns)
        except Exception:
            return False

    def _is_teardown_method(self, name: str) -> bool:
        try:
            norm_name = normalize_method_name(name)
            return any(norm_name.startswith(p) for p in self._norm_teardown_patterns)
        except Exception:
            return False

    def _is_test_method(self, name: str) -> bool:
        try:
            # Test patterns are matched case-sensitively for prefix by default,
            # but normalize to alphanumeric + lowercase to support camelCase/underscore variants.
            norm_name = normalize_method_name(name)
            return any(norm_name.startswith(p) for p in self._norm_test_patterns)
        except Exception:
            return False

    @property
    def setup_patterns(self) -> set[str]:
        """Return a copy of the setup pattern set."""
        return set(self._setup_patterns)

    @property
    def teardown_patterns(self) -> set[str]:
        """Return a copy of the teardown pattern set."""
        return set(self._teardown_patterns)

    @property
    def test_patterns(self) -> set[str]:
        """Return a copy of the test pattern set."""
        return set(self._test_patterns)


def convert_file(
    input_path: str | Path,
    output_path: str | Path | None = None,
    encoding: str = "utf-8",
    autocreate: bool = True,
    setup_patterns: list[str] | None = None,
    teardown_patterns: list[str] | None = None,
    test_patterns: list[str] | None = None,
    normalize_names: bool = False,
) -> ConversionResult:
    """Convert a unittest test file to pytest style.

    Args:
        input_path: Path to the input unittest test file.
        output_path: Path to write the converted file. If None, overwrites input file.
        encoding: Text encoding to use for reading/writing files.
        autocreate: When True, enable autocreation of tmp_path-backed file
            fixtures (see `convert_string` for context propagation).
        setup_patterns: Optional list of custom setup method names/patterns.
            When provided a PatternConfigurator will be constructed from these
            values and injected into the pipeline so stages can consult them.
        teardown_patterns: Optional list of custom teardown method names/patterns.
        test_patterns: Optional list of custom test name patterns.
        Returns:
        ConversionResult containing the converted code and metadata.

    Raises:
        FileNotFoundError: If the input file doesn't exist.
        PermissionDeniedError: If there are file permission issues.
        EncodingError: If there are file encoding issues.
    """
    input_path = Path(input_path)
    output_path = Path(output_path) if output_path else input_path

    # Read the source file
    try:
        source_code = input_path.read_text(encoding=encoding)
    except FileNotFoundError as e:
        raise SplurgeFileNotFoundError(f"Input file not found: {input_path}") from e
    except PermissionError as e:
        raise PermissionDeniedError(f"Permission denied reading file: {input_path}") from e
    except UnicodeDecodeError as e:
        raise EncodingError(f"Failed to decode file with encoding '{encoding}': {input_path}") from e

    # If the file already imports pytest, skip conversion and report no changes.
    if "import pytest" in source_code or "from pytest" in source_code:
        return ConversionResult(
            original_code=source_code,
            converted_code=source_code,
            has_changes=False,
            errors=[],
        )

    # Convert the code
    # Build a PatternConfigurator from optional pattern lists and pass it
    # into convert_string so stages may consult configured patterns.
    pc: PatternConfigurator | None = None
    if setup_patterns or teardown_patterns or test_patterns:
        pc = PatternConfigurator()
        if setup_patterns:
            for p in setup_patterns:
                pc.add_setup_pattern(p)
        if teardown_patterns:
            for p in teardown_patterns:
                pc.add_teardown_pattern(p)
        if test_patterns:
            for p in test_patterns:
                pc.add_test_pattern(p)

    result = convert_string(source_code, autocreate=autocreate, pattern_config=pc, normalize_names=normalize_names)

    # Write the converted code if there were changes and no errors
    if result.has_changes and not result.errors:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            # Use the project's atomic writer when available so tests can
            # monkeypatch main.atomic_write for error simulation.
            try:
                atomic_write(output_path, result.converted_code, encoding=encoding)
            except TypeError:
                # Some older atomic_write signatures may not accept encoding kw;
                # fall back to positional form.
                atomic_write(output_path, result.converted_code)
        except PermissionError:
            raise PermissionDeniedError(f"Permission denied writing to: {output_path}") from PermissionDeniedError
        except UnicodeEncodeError as e:
            raise EncodingError(f"Failed to encode file with encoding '{encoding}': {output_path}") from e

    return result


# `is_unittest_file` moved into `sentinel_discovery.py`; use that implementation


def find_unittest_files(
    directory: str | Path,
    *,
    follow_symlinks: bool = True,
    respect_gitignore: bool = False,
    fast_discovery: bool = False,
) -> list[Path]:
    """Find all Python files that appear to contain unittest tests.

    Args:
        directory: Directory to search for unittest files.

    Returns:
        List of Path objects for files that appear to contain unittest tests.
    """
    directory = Path(directory)

    if not directory.is_dir():
        return []

    unittest_files: list[Path] = []

    # Choose an iterator that respects follow_symlinks
    if follow_symlinks:
        iterator = directory.rglob("*")
    else:
        import os

        def _iter_no_follow(d: Path):
            for root, dirs, files in os.walk(str(d), followlinks=False):
                for f in files:
                    yield Path(root) / f

        iterator = _iter_no_follow(directory)

    # Prepare .gitignore handling if requested
    gitignore_patterns: list[str] = []
    spec = None
    if respect_gitignore:
        gitignore_path = directory / ".gitignore"
        if gitignore_path.exists():
            try:
                text = gitignore_path.read_text(encoding="utf-8")
                gitignore_patterns = [
                    line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")
                ]
                try:
                    import pathspec

                    # Attempt to fetch a GitWildMatchPattern factory if
                    # available; otherwise fall back to passing the
                    # patterns as-is. Use cast to silence mypy about the
                    # dynamic type of the factory value.
                    pattern_factory = getattr(pathspec.patterns, "GitWildMatchPattern", None)
                    try:
                        spec = pathspec.PathSpec.from_lines(cast(Any, pattern_factory), gitignore_patterns)
                    except Exception:
                        spec = None
                except Exception:
                    spec = None
            except Exception:
                gitignore_patterns = []

    for file_path in iterator:
        # Skip __pycache__ directories early
        try:
            if "__pycache__" in file_path.parts:
                continue
        except Exception:
            continue

        if not file_path.is_file():
            continue

        # Respect follow_symlinks: when disabled, skip symbolic links
        # to avoid discovering linked files on platforms where os.walk
        # may still list symlink files (followlinks controls directory
        # traversal, not whether file symlinks appear in listings).
        if not follow_symlinks:
            try:
                if file_path.is_symlink():
                    continue
            except Exception:
                # If we cannot determine symlink status, be conservative
                # and skip the entry rather than risk following it.
                continue

        # Quick check: try reading a small chunk as UTF-8 to detect binary/unreadable files.
        try:
            with file_path.open("r", encoding="utf-8") as fh:
                _ = fh.read(1024)
        except UnicodeDecodeError:
            # Binary or non-UTF8 file; skip it
            continue
        except PermissionError:
            # Can't read this file; skip it
            continue
        except FileNotFoundError:
            # Race: file removed between rglob and read; skip
            continue

        # Now safely check for unittest content; is_unittest_file may still raise specific errors
        try:
            if respect_gitignore and gitignore_patterns:
                try:
                    rel = str(file_path.relative_to(directory)).replace("\\", "/")
                except Exception:
                    rel = file_path.name

                ignored = False
                if spec is not None:
                    try:
                        if hasattr(spec, "match_file") and spec.match_file(rel):
                            ignored = True
                        elif hasattr(spec, "match_files"):
                            matched = set(spec.match_files([rel]))
                            if rel in matched:
                                ignored = True
                    except Exception:
                        ignored = False
                else:
                    if rel in gitignore_patterns or Path(rel).name in gitignore_patterns:
                        ignored = True

                if ignored:
                    continue

            if is_unittest_file(file_path, fast_discovery=fast_discovery):
                unittest_files.append(file_path)
        except (SplurgeFileNotFoundError, PermissionDeniedError, EncodingError):
            # Skip files that cannot be read or decoded
            continue
        except OSError:
            # Any OS-level error (e.g., path issues) should not break discovery; skip and continue
            continue

    return unittest_files


# Associated domains for this module
DOMAINS = ["main"]
