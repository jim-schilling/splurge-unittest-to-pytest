# Property Definitions for Core Components

This document defines the properties that should be tested with Hypothesis for the core components of splurge-unittest-to-pytest.

## Assert Transformer (`assert_ast_rewrites.py`)

### Core Properties

1. **Idempotence**: Transforming an already-transformed assertion should not change it further
   - `transform_assert_X(transform_assert_X(node)) == transform_assert_X(node)`

2. **Conservative Behavior**: Unknown or malformed input should return the original node unchanged
   - Invalid arguments → return original node
   - Missing arguments → return original node

3. **AST Validity**: All transformations should produce valid Python AST nodes
   - Output should be parseable by libcst
   - Output should be convertible back to valid Python code

4. **Semantic Equivalence**: Transformed assertions should be semantically equivalent to originals
   - `self.assertEqual(a, b)` → `assert a == b`
   - `self.assertTrue(x)` → `assert x`
   - `self.assertIsNone(x)` → `assert x is None`

5. **Parentheses Preservation**: Parentheses around expressions should be preserved when semantically important
   - `(a + b) == c` should maintain parentheses if needed for precedence

### Input Strategies

- Valid unittest assertion calls with various argument types
- Malformed calls (wrong number of args, invalid types)
- Nested expressions and complex comparisons
- Calls with keyword arguments

## Import Transformer (`import_transformer.py`)

### Core Properties

1. **Import Addition**: Should add missing imports without duplicating existing ones
   - If `pytest` already imported → don't add again
   - If `pytest` missing → add exactly one import

2. **No Modification**: Should not modify code when no changes needed
   - Input without unittest imports → output unchanged
   - Input with all required imports → output unchanged

3. **Import Ordering**: Should maintain proper import ordering (stdlib, third-party, local)

4. **Syntax Preservation**: Should not break Python syntax
   - Output should be valid Python code
   - Should handle various import statement formats

### Input Strategies

- Python source code with/without existing imports
- Various import statement formats (import, from...import)
- Code with syntax errors (should be handled gracefully)
- Empty or minimal Python files

## CLI Components (`cli.py`, `cli_adapters.py`)

### Core Properties

1. **Argument Validation**: Invalid arguments should be rejected with clear error messages
   - Non-existent files → error
   - Invalid patterns → error
   - Conflicting options → error

2. **Path Handling**: Should handle various path formats correctly
   - Absolute/relative paths
   - Windows/Unix path separators
   - Non-existent directories

3. **Configuration Building**: CLI args should map correctly to configuration objects
   - Each CLI option should set corresponding config field
   - Default values should be applied when options not provided

4. **Output Consistency**: Same inputs should produce same outputs (deterministic behavior)

### Input Strategies

- Valid file paths and glob patterns
- Invalid paths and malformed patterns
- Various combinations of CLI options
- Edge cases (empty directories, very long paths)

## Config Validation (`config_validation.py`)

### Core Properties

1. **Schema Validation**: Invalid configurations should be rejected
   - Type mismatches → validation error
   - Out-of-range values → validation error
   - Missing required fields → validation error

2. **Default Application**: Missing optional fields should get correct defaults
   - Partial configs should be completed with defaults
   - Defaults should be reasonable and safe

3. **Field Constraints**: Field values should respect their defined constraints
   - Numeric ranges (line_length: 60-200)
   - String patterns (file patterns)
   - Boolean logic (mutually exclusive options)

4. **Serialization**: Valid configs should round-trip through serialization
   - Config → dict → Config should preserve all values

### Input Strategies

- Valid configuration dictionaries
- Invalid configs (wrong types, out-of-range values)
- Partial configs missing various fields
- Edge case values (boundaries of ranges, empty collections)

## General Properties (All Components)

1. **Error Handling**: Components should handle errors gracefully
   - Invalid inputs → meaningful error messages or conservative fallbacks
   - Resource exhaustion → appropriate limits or timeouts

2. **Performance**: Transformations should complete in reasonable time
   - Large files should not cause excessive processing time
   - Memory usage should be bounded

3. **Thread Safety**: Components should be safe to use concurrently
   - No shared mutable state between operations
   - Reentrant functions where appropriate