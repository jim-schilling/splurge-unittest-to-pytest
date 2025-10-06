"""Hypothesis strategies for property-based testing.

This module defines strategies for generating test inputs for the
splurge-unittest-to-pytest library components.
"""

from typing import Any

import libcst as cst
from hypothesis import strategies as st

# Basic building blocks
identifiers = st.from_regex(r"[a-zA-Z_][a-zA-Z0-9_]*", fullmatch=True)


@st.composite
def cst_names(draw) -> cst.Name:
    """Generate libcst Name nodes."""
    value = draw(identifiers)
    return cst.Name(value=value)


@st.composite
def cst_integers(draw) -> cst.Integer:
    """Generate libcst Integer nodes."""
    value = draw(st.integers(min_value=1, max_value=100))
    return cst.Integer(value=str(value))


@st.composite
def cst_expressions(draw) -> cst.BaseExpression:
    """Generate various libcst expression nodes."""
    return draw(
        st.one_of(
            cst_names(),
            cst_integers(),
        )
    )


@st.composite
def cst_call_args(draw) -> list[cst.Arg]:
    """Generate arguments for a function call."""
    num_args = draw(st.integers(min_value=0, max_value=3))
    args = []
    for _ in range(num_args):
        value = draw(cst_expressions())
        args.append(cst.Arg(value=value))
    return args


@st.composite
def unittest_assertion_calls(draw) -> cst.Call:
    """Generate unittest assertion method calls."""
    assertion_methods = ["assertEqual", "assertTrue", "assertFalse", "assertIsNone"]

    method_name = draw(st.sampled_from(assertion_methods))
    args = draw(cst_call_args())

    return cst.Call(func=cst.Attribute(value=cst.Name(value="self"), attr=cst.Name(value=method_name)), args=args)


@st.composite
def python_source_code(draw) -> str:
    """Generate simple Python source code snippets."""
    statements = []
    num_imports = draw(st.integers(min_value=0, max_value=2))
    for _ in range(num_imports):
        module = draw(identifiers)
        statements.append(f"import {module}")

    if statements:
        return "\n".join(statements)
    else:
        return "pass"


@st.composite
def migration_configs(draw) -> dict[str, Any]:
    """Generate migration configuration dictionaries."""
    return {
        "line_length": draw(st.one_of(st.none(), st.integers(min_value=60, max_value=200))),
        "dry_run": draw(st.booleans()),
        "transform_assertions": draw(st.booleans()),
    }


@st.composite
def unittest_source_files(draw) -> str:
    """Generate complete unittest source files with various structures."""
    # Generate class name
    class_name = draw(st.from_regex(r"Test[A-Z][a-zA-Z0-9]*", fullmatch=True))

    # Generate test methods
    num_methods = draw(st.integers(min_value=1, max_value=5))
    methods = []

    for _ in range(num_methods):
        method_name = draw(st.from_regex(r"test_[a-z][a-zA-Z0-9_]*", fullmatch=True))

        # Generate method body with assertions
        num_assertions = draw(st.integers(min_value=1, max_value=3))
        assertions = []

        for _ in range(num_assertions):
            assertion_type = draw(
                st.sampled_from(
                    ["assertEqual", "assertTrue", "assertFalse", "assertIsNone", "assertIsNotNone", "assertRaises"]
                )
            )

            if assertion_type == "assertEqual":
                assertions.append("        self.assertEqual(1 + 1, 2)")
            elif assertion_type == "assertTrue":
                assertions.append("        self.assertTrue(True)")
            elif assertion_type == "assertFalse":
                assertions.append("        self.assertFalse(False)")
            elif assertion_type == "assertIsNone":
                assertions.append("        self.assertIsNone(None)")
            elif assertion_type == "assertIsNotNone":
                assertions.append("        self.assertIsNotNone(42)")
            elif assertion_type == "assertRaises":
                assertions.append("        with self.assertRaises(ValueError):\n            raise ValueError('test')")

        method_body = "\n".join(assertions)
        methods.append(f"    def {method_name}(self):\n{method_body}")

    # Generate setUp method sometimes
    has_setup = draw(st.booleans())
    setup_method = ""
    if has_setup:
        setup_method = "    def setUp(self):\n        self.value = 42\n\n"

    # Generate tearDown method sometimes
    has_teardown = draw(st.booleans())
    teardown_method = ""
    if has_teardown:
        teardown_method = "    def tearDown(self):\n        pass\n\n"

    # Construct the full file
    imports = "import unittest\n\n"
    class_def = f"class {class_name}(unittest.TestCase):\n"
    class_body = setup_method + teardown_method + "\n".join(methods)

    return imports + class_def + class_body
