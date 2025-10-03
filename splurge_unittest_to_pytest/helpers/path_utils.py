"""Cross-platform path utilities for enhanced path handling.

This module provides utilities for path validation, normalization, and
enhanced error handling to improve cross-platform compatibility and
user experience with path-related operations.

Copyright (c) 2025 Jim Schilling
This software is released under the MIT License.
"""

import platform
from pathlib import Path

from ..exceptions import ValidationError


class PathValidationError(ValidationError):
    """Raised when path validation fails."""

    def __init__(self, message: str, path: str, validation_type: str = "path"):
        self.path = path
        self.validation_type = validation_type
        super().__init__(message, validation_type, field=path)


def validate_source_path(source_path: str | Path) -> Path:
    """Validate and normalize a source file path.

    Args:
        source_path: Path to validate (string or Path object)

    Returns:
        Normalized Path object

    Raises:
        PathValidationError: If path validation fails
    """
    try:
        path = Path(source_path)
        path_str = str(path)

        # Check for empty path
        if not path_str.strip():
            raise PathValidationError("Source path cannot be empty", path_str, "empty_path")

        # Check for path length limits (Windows has 260 char limit)
        if len(path_str) > 260 and platform.system() == "Windows":
            raise PathValidationError(
                f"Path length exceeds Windows limit of 260 characters: {len(path_str)}", path_str, "path_length"
            )

        # Check for invalid characters in path name
        invalid_chars = '<>:"|?*'
        if any(char in path.name for char in invalid_chars):
            raise PathValidationError(f"Path contains invalid characters: {invalid_chars}", path_str, "invalid_chars")

        return path

    except (OSError, ValueError) as e:
        raise PathValidationError(f"Invalid path format: {e}", str(source_path), "path_format") from e


def validate_target_path(target_path: str | Path, create_parent: bool = True) -> Path:
    """Validate a target file path without performing side-effects.

    This function performs only pure validation and does not create
    directories or modify the filesystem. To perform the side-effect of
    ensuring the parent directory exists, call `ensure_parent_dir()`.

    Args:
        target_path: Target path to validate

    Returns:
        Normalized and validated Path object

    Raises:
        PathValidationError: If path validation fails
    """
    try:
        path = Path(target_path)

        # Basic validation checks that do not modify the FS
        if not str(path).strip():
            raise PathValidationError("Target path cannot be empty", str(path), "empty_path")

        # Check for invalid characters in path name
        invalid_chars = '<>:"|?*'
        if any(char in path.name for char in invalid_chars):
            raise PathValidationError(f"Path contains invalid characters: {invalid_chars}", str(path), "invalid_chars")

        return path

    except (OSError, ValueError) as e:
        raise PathValidationError(f"Invalid target path: {e}", str(target_path), "target_format") from e


def ensure_parent_dir(target_path: str | Path, exist_ok: bool = True) -> None:
    """Side-effect: ensure the parent directory of target_path exists.

    This function performs the filesystem modification previously baked
    into `validate_target_path`.
    """
    path = Path(target_path)
    try:
        if path.parent:
            path.parent.mkdir(parents=True, exist_ok=exist_ok)
    except (OSError, PermissionError) as e:
        raise PathValidationError(f"Cannot create parent directory: {e}", str(path.parent), "parent_creation") from e


def normalize_path_for_display(path: str | Path, force_posix: bool = False) -> str:
    """Normalize a path for consistent display across platforms.

    Args:
        path: Path to normalize
        force_posix: Force POSIX-style path separators

    Returns:
        Normalized path string for display
    """
    path_obj = Path(path)

    if force_posix or platform.system() != "Windows":
        return path_obj.as_posix()
    else:
        return str(path_obj)


def get_path_info(path: str | Path) -> dict:
    """Get comprehensive information about a path.

    Args:
        path: Path to analyze

    Returns:
        Dictionary containing path information
    """
    path_obj = Path(path)

    info = {
        "original": str(path),
        "normalized": str(path_obj.resolve()) if path_obj.exists() else str(path_obj),
        "absolute": str(path_obj.absolute()),
        "exists": path_obj.exists(),
        "is_file": path_obj.is_file() if path_obj.exists() else False,
        "is_dir": path_obj.is_dir() if path_obj.exists() else False,
        "parent": str(path_obj.parent),
        "name": path_obj.name,
        "suffix": path_obj.suffix,
        "stem": path_obj.stem,
    }

    # Add platform-specific information
    if platform.system() == "Windows":
        info["posix_path"] = path_obj.as_posix()
    else:
        info["posix_path"] = str(path_obj)

    # Add size information if it's a file
    if path_obj.exists() and path_obj.is_file():
        try:
            info["size"] = path_obj.stat().st_size
        except (OSError, PermissionError):
            info["size"] = None

    return info


def suggest_path_fixes(error: Exception, path: str) -> list[str]:
    """Generate helpful suggestions for path-related errors.

    Args:
        error: The exception that occurred
        path: The path that caused the error

    Returns:
        List of suggested fixes
    """
    suggestions = []
    path_obj = Path(path)

    if isinstance(error, FileNotFoundError):
        if not path_obj.parent.exists():
            suggestions.append(f"Create the parent directory: {path_obj.parent}")
        suggestions.append(f"Check if the path exists: {path}")
        suggestions.append("Verify file permissions")

    elif isinstance(error, PermissionError):
        suggestions.append(f"Check write permissions for: {path_obj.parent}")
        suggestions.append("Try running with appropriate permissions or as administrator")
        if platform.system() == "Windows":
            suggestions.append("Check if file is open in another program")

    elif isinstance(error, OSError) and "name too long" in str(error):
        suggestions.append("Use a shorter path name")
        suggestions.append(f"Move files to a directory with shorter path: {path_obj.parent}")

    elif isinstance(error, OSError | ValueError):
        suggestions.append(f"Check if path contains valid characters: {path}")
        suggestions.append("Use absolute paths instead of relative paths")

    # Add general suggestions
    suggestions.append(f"Verify the path exists and is accessible: {path}")

    return suggestions


def safe_path_operation(operation_name: str, path: str | Path, operation_func):
    """Safely execute a path-related operation with enhanced error handling.

    Args:
        operation_name: Name of the operation for error reporting
        path: Path being operated on
        operation_func: Function to execute

    Returns:
        Result of operation_func

    Raises:
        PathValidationError: If operation fails with path-related error
    """
    try:
        return operation_func()
    except (FileNotFoundError, PermissionError, OSError) as e:
        raise PathValidationError(
            f"Path operation '{operation_name}' failed: {e}", str(path), "operation_failure"
        ) from e
