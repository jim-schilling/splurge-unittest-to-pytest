"""Main conversion functions and utilities."""

from dataclasses import dataclass
from pathlib import Path

import libcst as cst

from .converter import UnittestToPytestTransformer
from .stages.pipeline import run_pipeline
from .exceptions import EncodingError, FileNotFoundError as SplurgeFileNotFoundError, PermissionDeniedError


@dataclass
class ConversionResult:
    """Result of a unittest to pytest conversion."""
    
    original_code: str
    converted_code: str
    has_changes: bool
    errors: list[str]


def convert_string(
    source_code: str,
    setup_patterns: list[str] | None = None,
    teardown_patterns: list[str] | None = None,
    test_patterns: list[str] | None = None,
    compat: bool = True,
    engine: str = "transformer",
) -> ConversionResult:
    """Convert unittest-style test code to pytest-style.

    Args:
        source_code: The original unittest test code as a string.
        setup_patterns: Optional list of setup method patterns to use.
        teardown_patterns: Optional list of teardown method patterns to use.
        test_patterns: Optional list of test method patterns to use.

    Returns:
        ConversionResult containing the converted code and metadata.
    """
    errors: list[str] = []
    
    try:
        # Parse the source code into a CST
        tree = cst.parse_module(source_code)

        # Apply the chosen conversion engine
        if engine == "pipeline":
            # run staged pipeline (returns a Module)
            converted_module = run_pipeline(tree, compat=compat)
            converted_code = converted_module.code
        else:
            # legacy transformer
            transformer = UnittestToPytestTransformer(compat=compat)

            # Apply custom patterns if provided
            if setup_patterns:
                for pattern in setup_patterns:
                    transformer.add_setup_pattern(pattern)
            if teardown_patterns:
                for pattern in teardown_patterns:
                    transformer.add_teardown_pattern(pattern)
            if test_patterns:
                for pattern in test_patterns:
                    transformer.add_test_pattern(pattern)

            converted_tree = tree.visit(transformer)
            converted_code = converted_tree.code

        # Check if any changes were made
        has_changes = converted_code != source_code

        return ConversionResult(
            original_code=source_code,
            converted_code=converted_code,
            has_changes=has_changes,
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
def convert_file(
    input_path: str | Path, 
    output_path: str | Path | None = None,
    encoding: str = "utf-8",
    setup_patterns: list[str] | None = None,
    teardown_patterns: list[str] | None = None,
    test_patterns: list[str] | None = None,
    compat: bool = True,
    engine: str = "transformer",
) -> ConversionResult:
    """Convert a unittest test file to pytest style.
    
    Args:
        input_path: Path to the input unittest test file.
        output_path: Path to write the converted file. If None, overwrites input file.
        encoding: Text encoding to use for reading/writing files.
        
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
    
    # Convert the code
    result = convert_string(
        source_code,
        setup_patterns=setup_patterns,
        teardown_patterns=teardown_patterns,
    test_patterns=test_patterns,
    compat=compat,
    engine=engine,
    )
    
    # Write the converted code if there were changes and no errors
    if result.has_changes and not result.errors:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result.converted_code, encoding=encoding)
        except PermissionError:
            raise PermissionDeniedError(f"Permission denied writing to: {output_path}") from PermissionError
        except UnicodeEncodeError as e:
            raise EncodingError(f"Failed to encode file with encoding '{encoding}': {output_path}") from e
    
    return result


def is_unittest_file(file_path: str | Path) -> bool:
    """Check if a Python file appears to contain unittest-style tests.
    
    Args:
        file_path: Path to the Python file to check.
        
    Returns:
        True if the file appears to contain unittest tests, False otherwise.
        
    Raises:
        FileNotFoundError: If the file doesn't exist.
        PermissionDeniedError: If file permissions prevent reading.
        EncodingError: If file encoding issues occur.
    """
    file_path = Path(file_path)
    
    try:
        exists = file_path.exists()
    except PermissionError as e:
        raise PermissionDeniedError(f"Permission denied checking file: {file_path}") from e
    
    if not exists:
        raise SplurgeFileNotFoundError(f"File not found: {file_path}")
    
    try:
        content = file_path.read_text(encoding="utf-8")
        
        # Skip files that are already using pytest
        if "import pytest" in content or "from pytest" in content:
            return False
        
        # Simple heuristics to detect unittest files
        unittest_indicators = [
            "import unittest",
            "from unittest",
            "unittest.TestCase",
            "class Test",
            "def test_",
            "setUp(",
            "tearDown(",
            "self.assert",
        ]
        
        return any(indicator in content for indicator in unittest_indicators)
        
    except PermissionError:
        raise PermissionDeniedError(f"Permission denied reading file: {file_path}") from PermissionError
    except UnicodeDecodeError as e:
        raise EncodingError(f"Failed to decode file with UTF-8 encoding: {file_path}") from e


def find_unittest_files(directory: str | Path) -> list[Path]:
    """Find all Python files that appear to contain unittest tests.
    
    Args:
        directory: Directory to search for unittest files.
        
    Returns:
        List of Path objects for files that appear to contain unittest tests.
    """
    directory = Path(directory)
    
    if not directory.is_dir():
        return []
    
    unittest_files = []
    
    for file_path in directory.rglob("*"):
        # Skip __pycache__ directories early
        try:
            if "__pycache__" in file_path.parts:
                continue
        except Exception:
            # Defensive: if Path.parts access fails for some reason, skip this path
            continue

        if not file_path.is_file():
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
            if is_unittest_file(file_path):
                unittest_files.append(file_path)
        except (SplurgeFileNotFoundError, PermissionDeniedError, EncodingError):
            # Skip files that cannot be read or decoded
            continue
        except OSError:
            # Any OS-level error (e.g., path issues) should not break discovery; skip and continue
            continue
    
    return unittest_files