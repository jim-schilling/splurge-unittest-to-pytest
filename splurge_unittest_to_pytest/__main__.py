"""Main conversion functions and utilities."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import libcst as cst

from .converter import UnittestToPytestTransformer


@dataclass
class ConversionResult:
    """Result of a unittest to pytest conversion."""
    
    original_code: str
    converted_code: str
    has_changes: bool
    errors: list[str]


def convert_string(source_code: str) -> ConversionResult:
    """Convert unittest-style test code to pytest-style.
    
    Args:
        source_code: The original unittest test code as a string.
        
    Returns:
        ConversionResult containing the converted code and metadata.
        
    Raises:
        cst.ParserError: If the source code cannot be parsed.
    """
    errors = []
    
    try:
        # Parse the source code into a CST
        tree = cst.parse_module(source_code)
        
        # Apply the transformation
        transformer = UnittestToPytestTransformer()
        converted_tree = tree.visit(transformer)
        
        # Generate the converted code
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
            converted_code=source_code,
            has_changes=False,
            errors=errors,
        )


def convert_file(
    input_path: Union[str, Path], 
    output_path: Optional[Union[str, Path]] = None,
    encoding: str = "utf-8"
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
        PermissionError: If there are file permission issues.
    """
    input_path = Path(input_path)
    output_path = Path(output_path) if output_path else input_path
    
    # Read the source file
    try:
        source_code = input_path.read_text(encoding=encoding)
    except FileNotFoundError:
        raise FileNotFoundError(f"Input file not found: {input_path}")
    except PermissionError:
        raise PermissionError(f"Permission denied reading file: {input_path}")
    
    # Convert the code
    result = convert_string(source_code)
    
    # Write the converted code if there were changes and no errors
    if result.has_changes and not result.errors:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(result.converted_code, encoding=encoding)
        except PermissionError:
            result.errors.append(f"Permission denied writing to: {output_path}")
    
    return result


def is_unittest_file(file_path: Union[str, Path]) -> bool:
    """Check if a Python file appears to contain unittest-style tests.
    
    Args:
        file_path: Path to the Python file to check.
        
    Returns:
        True if the file appears to contain unittest tests, False otherwise.
    """
    file_path = Path(file_path)
    
    if not file_path.exists() or file_path.suffix != ".py":
        return False
    
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
        
    except (UnicodeDecodeError, PermissionError):
        return False


def find_unittest_files(directory: Union[str, Path]) -> list[Path]:
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
    
    for file_path in directory.rglob("*.py"):
        if is_unittest_file(file_path):
            unittest_files.append(file_path)
    
    return unittest_files
