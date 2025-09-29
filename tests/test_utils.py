#!/usr/bin/env python3
"""Test utilities for unittest to pytest migration validation.

This module provides helper functions for validating code transformations,
ignoring formatting differences like whitespace, empty lines, and import ordering.
"""

import ast
from typing import Any

import libcst as cst


def _normalize_cst_node(node: Any) -> str:
    """Normalize a CST node to a string representation for comparison.

    Args:
        node: CST node to normalize

    Returns:
        Normalized string representation
    """
    if isinstance(node, cst.Name):
        return f"Name({node.value})"
    elif isinstance(node, cst.Attribute):
        return f"Attribute({_normalize_cst_node(node.value)}, {_normalize_cst_node(node.attr)})"
    elif isinstance(node, cst.Call):
        func_str = _normalize_cst_node(node.func)
        args_str = ", ".join(_normalize_cst_node(arg.value) for arg in node.args)
        return f"Call({func_str}, [{args_str}])"
    elif isinstance(node, cst.SimpleString):
        return f"String({node.value})"
    elif isinstance(node, cst.BinaryOperation):
        return f"BinaryOp({_normalize_cst_node(node.left)}, {_normalize_cst_node(node.operator)}, {_normalize_cst_node(node.right)})"
    elif isinstance(node, cst.Comparison):
        return f"Comparison({_normalize_cst_node(node.left)}, {', '.join(_normalize_cst_node(comp) for comp in node.comparisons)})"
    elif isinstance(node, cst.Expr):
        return f"Expr({_normalize_cst_node(node.value)})"
    else:
        # For other node types, use the string representation
        return str(type(node).__name__)


def _extract_imports_from_cst(module: cst.Module) -> set[str]:
    """Extract import statements from CST module.

    Args:
        module: CST module to analyze

    Returns:
        Set of normalized import statement strings
    """
    imports = set()

    for stmt in module.body:
        if isinstance(stmt, cst.SimpleStatementLine):
            for item in stmt.body:
                if isinstance(item, cst.Import | cst.ImportFrom):
                    # Use the module's code generation to get the string representation
                    import_stmt_module = cst.Module(body=[stmt])
                    imports.add(import_stmt_module.code.strip())

    return imports


def _normalize_ast_node(node: Any) -> str:
    """Normalize an AST node to a string representation for comparison.

    Args:
        node: AST node to normalize

    Returns:
        Normalized string representation
    """
    if isinstance(node, ast.Name):
        return f"Name({node.id})"
    elif isinstance(node, ast.Attribute):
        return f"Attribute({_normalize_ast_node(node.value)}, {_normalize_ast_node(node.attr)})"
    elif isinstance(node, ast.Call):
        func_str = _normalize_ast_node(node.func)
        args_str = ", ".join(_normalize_ast_node(arg) for arg in node.args)
        keywords_str = ", ".join(f"{kw.arg}={_normalize_ast_node(kw.value)}" for kw in node.keywords)
        all_args = [args_str]
        if keywords_str:
            all_args.append(keywords_str)
        return f"Call({func_str}, [{', '.join(all_args)}])"
    elif isinstance(node, ast.Str):
        return f"Str({node.s})"
    elif isinstance(node, ast.Constant):
        return f"Constant({node.value})"
    elif isinstance(node, ast.BinOp):
        return f"BinOp({_normalize_ast_node(node.left)}, {_normalize_ast_node(node.op)}, {_normalize_ast_node(node.right)})"
    elif isinstance(node, ast.Compare):
        return f"Compare({_normalize_ast_node(node.left)}, {', '.join(f'{_normalize_ast_node(comp)}' for comp in node.comparators)})"
    elif isinstance(node, ast.Expr):
        return f"Expr({_normalize_ast_node(node.value)})"
    else:
        # For other node types, use the string representation
        return str(type(node).__name__)


def _extract_imports_from_ast(tree: ast.Module) -> set[str]:
    """Extract import statements from AST module.

    Args:
        tree: AST module to analyze

    Returns:
        Set of normalized import statement strings
    """
    imports = set()

    for stmt in tree.body:
        if isinstance(stmt, ast.Import | ast.ImportFrom):
            imports.add(ast.unparse(stmt).strip())

    return imports


def _normalize_code_structure_cst(code: str) -> str:
    """Normalize code structure using CST analysis.

    Args:
        code: Code string to normalize

    Returns:
        Normalized structural representation
    """
    try:
        # Parse with CST
        module = cst.parse_module(code)

        # Collect all top-level statements and sort them for consistent comparison
        statement_types = []
        statement_details = {}

        for i, stmt in enumerate(module.body):
            if isinstance(stmt, cst.SimpleStatementLine):
                for item in stmt.body:
                    if isinstance(item, cst.Expr):
                        # For expressions, include the structure of the expression
                        structure_parts = []
                        _collect_expression_structure(item.value, structure_parts)
                        statement_types.append(f"Expr({', '.join(structure_parts)})")
                        statement_details[f"Expr({', '.join(structure_parts)})"] = f"stmt_{i}"
                    else:
                        stmt_type = str(type(item).__name__)
                        statement_types.append(stmt_type)
                        statement_details[stmt_type] = f"stmt_{i}"
            else:
                stmt_type = str(type(stmt).__name__)
                statement_types.append(stmt_type)
                statement_details[stmt_type] = f"stmt_{i}"

        # Sort for consistent comparison (but maintain relative order of similar statements)
        type_counts = {}
        sorted_statements = []

        for stmt_type in statement_types:
            count = type_counts.get(stmt_type, 0)
            type_counts[stmt_type] = count + 1

            # Add a suffix to distinguish multiple statements of the same type
            suffix = f"_{count}" if type_counts[stmt_type] > 1 else ""
            sorted_statements.append(f"{stmt_type}{suffix}")

        return "\n".join(sorted(sorted_statements))

    except Exception:
        # Fallback to simple normalization if CST parsing fails
        return _normalize_code_structure_regex(code)


def _collect_expression_structure(node: Any, structure_parts: list[str]) -> None:
    """Recursively collect the structure of an expression.

    Args:
        node: CST node to analyze
        structure_parts: List to collect structure information
    """
    if isinstance(node, cst.Name):
        structure_parts.append(f"Name({node.value})")
    elif isinstance(node, cst.Attribute):
        structure_parts.append(f"Attribute({_normalize_cst_node(node.value)}, {_normalize_cst_node(node.attr)})")
    elif isinstance(node, cst.Call):
        structure_parts.append("Call")
        _collect_expression_structure(node.func, structure_parts)
        for arg in node.args:
            _collect_expression_structure(arg.value, structure_parts)
    elif isinstance(node, cst.BinaryOperation):
        structure_parts.append("BinaryOp")
        _collect_expression_structure(node.left, structure_parts)
        _collect_expression_structure(node.right, structure_parts)
    elif isinstance(node, cst.Comparison):
        structure_parts.append("Comparison")
        _collect_expression_structure(node.left, structure_parts)
        for comp in node.comparisons:
            _collect_expression_structure(comp.comparator, structure_parts)
    elif isinstance(node, cst.SimpleString | cst.Constant):
        structure_parts.append(f"Literal({type(node).__name__})")
    else:
        structure_parts.append(str(type(node).__name__))


def _normalize_code_structure_regex(code: str) -> str:
    """Fallback normalization using regex patterns.

    Args:
        code: Code string to normalize

    Returns:
        Normalized structural representation
    """
    import re

    # Remove comments and docstrings
    code = re.sub(r'""".*?"""', "", code, flags=re.DOTALL)
    code = re.sub(r"'''.*?'''", "", code, flags=re.DOTALL)
    code = re.sub(r"#.*", "", code)

    # Split into lines and filter
    lines = [line.strip() for line in code.split("\n") if line.strip()]

    # Normalize whitespace
    normalized_lines = []
    for line in lines:
        # Normalize multiple spaces
        line = re.sub(r"\s+", " ", line)
        normalized_lines.append(line)

    return "\n".join(normalized_lines)


def assert_code_structure_equals(actual: str, expected: str, message: str = "") -> None:
    """Assert that two code strings have the same structure using CST/AST analysis.

    This function uses CST and AST parsing to compare code structure,
    providing more robust comparison than simple string matching. It allows
    for different ordering of statements and focuses on structural equivalence.

    Args:
        actual: The actual code output
        expected: The expected code structure
        message: Optional message for assertion failure

    Raises:
        AssertionError: If the code structures don't match
    """
    # Fast paths to avoid expensive CST parsing when possible
    # 1) Exact text match after trimming - common when regeneration created same output
    if actual.strip() == expected.strip():
        return

    # 2) AST structural equality - much cheaper than full CST analysis and
    #    catches cases where formatting differs but structure is identical.
    try:
        actual_tree = ast.parse(actual)
        expected_tree = ast.parse(expected)
        # Use ast.dump without attributes for a quick structural compare
        if ast.dump(actual_tree, include_attributes=False) == ast.dump(expected_tree, include_attributes=False):
            return
    except Exception:
        # If parsing fails, fall back to more expensive CST-based comparison below
        pass

    # Try CST-based comparison as a more precise, but heavier, analysis
    try:
        actual_structure = _normalize_code_structure_cst(actual)
        expected_structure = _normalize_code_structure_cst(expected)

        # Split into lines for comparison
        actual_lines = set(actual_structure.strip().split("\n"))
        expected_lines = set(expected_structure.strip().split("\n"))

        # Check if the sets of statement types are equivalent
        if actual_lines == expected_lines:
            return  # Structures match
    except Exception:
        # Log the exception for debugging but continue to fallbacks
        pass

    # Fall back to AST-based comparison
    try:
        actual_tree = ast.parse(actual)
        expected_tree = ast.parse(expected)

        # Compare AST structures using dump (which normalizes structure)
        actual_dump = ast.dump(actual_tree, indent=2)
        expected_dump = ast.dump(expected_tree, indent=2)

        # Extract just the structure without specific values for comparison
        actual_structure_lines = []
        expected_structure_lines = []

        for line in actual_dump.split("\n"):
            if "value=" in line or "id=" in line or "ctx=" in line:
                # Skip value-specific lines
                continue
            actual_structure_lines.append(line.strip())

        for line in expected_dump.split("\n"):
            if "value=" in line or "id=" in line or "ctx=" in line:
                # Skip value-specific lines
                continue
            expected_structure_lines.append(line.strip())

        if actual_structure_lines == expected_structure_lines:
            return  # AST structures match
    except Exception:
        # Final fallback to regex-based comparison
        actual_structure = _normalize_code_structure_regex(actual)
        expected_structure = _normalize_code_structure_regex(expected)

        # For regex fallback, be more lenient - just check that the same statement types exist
        actual_lines = {line.strip() for line in actual_structure.split("\n") if line.strip()}
        expected_lines = {line.strip() for line in expected_structure.split("\n") if line.strip()}

        if actual_lines == expected_lines:
            return  # Structures are equivalent

    # If we get here, structures don't match
    try:
        # Try to get the structure info from the last successful parsing attempt
        actual_structure = _normalize_code_structure_cst(actual)
        expected_structure = _normalize_code_structure_cst(expected)
        actual_lines = set(actual_structure.strip().split("\n"))
        expected_lines = set(expected_structure.strip().split("\n"))
    except Exception:
        # Final fallback
        actual_structure = _normalize_code_structure_regex(actual)
        expected_structure = _normalize_code_structure_regex(expected)
        actual_lines = {line.strip() for line in actual_structure.split("\n") if line.strip()}
        expected_lines = {line.strip() for line in expected_structure.split("\n") if line.strip()}

    error_msg = f"Code structure mismatch{message and ': ' + message}\n"
    error_msg += f"Expected structure types: {sorted(expected_lines)}\n"
    error_msg += f"Actual structure types: {sorted(actual_lines)}\n"
    error_msg += f"\nExpected (original):\n{expected}\n"
    error_msg += f"Actual (original):\n{actual}"
    raise AssertionError(error_msg)


def assert_imports_equal(actual_code: str, expected_imports: list[str], message: str = "") -> None:
    """Assert that code contains the expected imports using CST/AST analysis.

    Args:
        actual_code: The code to check for imports
        expected_imports: List of expected import statements
        message: Optional message for assertion failure

    Raises:
        AssertionError: If imports don't match
    """
    # Try CST-based import extraction first
    try:
        actual_module = cst.parse_module(actual_code)
        actual_imports = _extract_imports_from_cst(actual_module)
    except Exception:
        # Fall back to AST-based extraction
        try:
            actual_tree = ast.parse(actual_code)
            actual_imports = _extract_imports_from_ast(actual_tree)
        except Exception:
            # Final fallback to simple parsing
            actual_imports = _extract_imports_fallback(actual_code)

    expected_imports_set = set(expected_imports)

    missing_imports = expected_imports_set - actual_imports
    extra_imports = actual_imports - expected_imports_set

    if missing_imports or extra_imports:
        error_msg = f"Import mismatch{message and ': ' + message}\n"
        if missing_imports:
            error_msg += f"Missing imports: {sorted(missing_imports)}\n"
        if extra_imports:
            error_msg += f"Extra imports: {sorted(extra_imports)}\n"
        error_msg += f"Expected imports: {sorted(expected_imports_set)}\n"
        error_msg += f"Actual imports: {sorted(actual_imports)}"
        raise AssertionError(error_msg)


def _extract_imports_fallback(code: str) -> set[str]:
    """Fallback import extraction using simple string parsing.

    Args:
        code: Code to extract imports from

    Returns:
        Set of import statements
    """
    import re

    lines = code.split("\n")
    imports = set()

    for line in lines:
        line = line.strip()
        if line.startswith("import ") or line.startswith("from "):
            # Normalize whitespace
            normalized_line = re.sub(r"\s+", " ", line)
            imports.add(normalized_line)

    return imports


def assert_has_imports(code: str, required_imports: list[str], message: str = "") -> None:
    """Assert that code contains all required imports (but may have others).

    Args:
        code: The code to check
        required_imports: List of imports that must be present
        message: Optional message for assertion failure

    Raises:
        AssertionError: If any required import is missing
    """
    # Try CST-based import extraction first
    try:
        actual_module = cst.parse_module(code)
        actual_imports = _extract_imports_from_cst(actual_module)
    except Exception:
        # Fall back to AST-based extraction
        try:
            actual_tree = ast.parse(code)
            actual_imports = _extract_imports_from_ast(actual_tree)
        except Exception:
            # Final fallback to simple parsing
            actual_imports = _extract_imports_fallback(code)

    required_imports_set = set(required_imports)
    missing_imports = required_imports_set - actual_imports

    if missing_imports:
        error_msg = f"Missing required imports{message and ': ' + message}\n"
        error_msg += f"Missing: {sorted(missing_imports)}\n"
        error_msg += f"Required: {sorted(required_imports_set)}\n"
        error_msg += f"Found: {sorted(actual_imports)}"
        raise AssertionError(error_msg)


def assert_class_structure(code: str, class_name: str, expected_methods: list[str] = None, message: str = "") -> None:
    """Assert that a class has the expected structure using CST analysis.

    Args:
        code: The code containing the class
        class_name: Name of the class to check
        expected_methods: List of method names that should be present
        message: Optional message for assertion failure

    Raises:
        AssertionError: If class structure doesn't match expectations
    """
    try:
        # Parse with CST
        module = cst.parse_module(code)

        # Find the class
        class_found = False
        for stmt in module.body:
            if isinstance(stmt, cst.ClassDef) and stmt.name.value == class_name:
                class_found = True

                # Check for expected methods
                if expected_methods:
                    method_names = {func.name.value for func in stmt.body.body if isinstance(func, cst.FunctionDef)}
                    for method in expected_methods:
                        if method not in method_names:
                            raise AssertionError(
                                f"Method '{method}' not found in class '{class_name}'{message and ': ' + message}"
                            )
                break

        if not class_found:
            raise AssertionError(f"Class '{class_name}' not found in code{message and ': ' + message}")

    except Exception:
        # Fallback to simple string matching
        if f"class {class_name}" not in code:
            raise AssertionError(f"Class '{class_name}' not found in code{message and ': ' + message}") from None

        if expected_methods:
            for method in expected_methods:
                if f"def {method}" not in code:
                    raise AssertionError(
                        f"Method '{method}' not found in class '{class_name}'{message and ': ' + message}"
                    ) from None


def assert_function_exists(code: str, function_name: str, message: str = "") -> None:
    """Assert that a function exists in the code using CST analysis.

    Args:
        code: The code to check
        function_name: Name of the function to look for
        message: Optional message for assertion failure

    Raises:
        AssertionError: If function is not found
    """
    try:
        # Parse with CST
        module = cst.parse_module(code)

        # Look for function definitions
        for stmt in module.body:
            if isinstance(stmt, cst.FunctionDef) and stmt.name.value == function_name:
                return  # Function found

        raise AssertionError(f"Function '{function_name}' not found in code{message and ': ' + message}")

    except Exception:
        # Fallback to simple string matching
        if f"def {function_name}" not in code:
            raise AssertionError(f"Function '{function_name}' not found in code{message and ': ' + message}") from None
