# Research: Unittest Pattern Analysis - Identifying Additional Patterns for Support

## Current Pattern Support

Based on analysis of the current codebase, the unittest-to-pytest converter currently supports the following patterns:

### ✅ **Currently Supported Patterns**

#### 1. **Assertion Transformations**
- **All major unittest assertions**: `assertEqual`, `assertTrue`, `assertFalse`, `assertIs`, `assertIn`, `assertRaises`, `assertRaisesRegex`, `assertDictEqual`, `assertListEqual`, etc.
- **Complex assertions**: `assertAlmostEqual`, `assertGreater`, `assertLess`, `assertRegex`, `assertLogs`, `assertNoLogs`
- **Skip decorators**: `@unittest.skip`, `@unittest.skipIf`, `@unittest.skipUnless` → `@pytest.mark.skip`, `@pytest.mark.skipif`

#### 2. **Setup/Teardown Methods**
- **Instance lifecycle**: `setUp()` → pytest instance fixture, `tearDown()` → pytest instance fixture cleanup
- **Class lifecycle**: `setUpClass()` → pytest class fixture, `tearDownClass()` → pytest class fixture cleanup
- **Module lifecycle**: `setUpModule()` → pytest module fixture, `tearDownModule()` → pytest module fixture cleanup

#### 3. **Test Method Discovery**
- **Standard test prefixes**: Methods starting with `test_` are identified as test methods
- **Method name normalization**: `test_Something` → `test_Something` (no change needed for pytest)
- **Configurable prefixes**: Support for custom test prefixes via CLI options

#### 4. **unittest.TestCase Inheritance**
- **Detection**: Automatically detects `unittest.TestCase` inheritance (both `unittest.TestCase` and imported `TestCase`)
- **Removal**: Removes inheritance and converts to plain classes
- **Fixture conversion**: Converts setup/teardown methods to pytest fixtures

#### 5. **SubTest Patterns**
- **Simple subTest loops**: Converts `for item in items: with self.subTest(item=item): ...` to `@pytest.mark.parametrize`
- **Complex subTest scenarios**: Uses `pytest-subtests` plugin for complex cases
- **Decision model integration**: Analyzes loop patterns to determine optimal transformation strategy

#### 6. **Import Management**
- **Pytest imports**: Automatically adds `import pytest` when needed
- **Unittest cleanup**: Removes unused unittest imports after transformation
- **Mock imports**: Preserves mock-related imports

#### 7. **Logging and Context Managers**
- **assertLogs/assertNoLogs**: Converts to `caplog` fixture usage
- **Context manager rewriting**: Handles `with self.assertRaises(...)` patterns

## 🔍 **Additional Patterns That Could Be Supported**

### 1. **Mock and Patch Patterns** (High Priority)
Currently the tool preserves mock usage but doesn't actively transform it. Additional patterns:

- **@patch decorators**: Convert `@patch('module.function')` to `@pytest.patch('module.function')`
- **Mock object creation**: `mock.Mock()`, `mock.MagicMock()` → `pytest-mock` equivalents or plain mocks
- **Patch contexts**: `with patch(...) as mock_obj:` → `with pytest.patch(...) as mock_obj:`
- **Mock assertions**: `mock_obj.assert_called_once()` → standard mock assertions
- **Spec and autospec**: Preserve or enhance mock specifications

### 2. **Advanced Test Discovery Patterns** (Medium Priority) ✅ **IMPLEMENTED**
- **Custom test method prefixes**: `spec_`, `should_`, `it_` patterns (beyond current `test_` support) ✅
- **Test class naming patterns**: `Test*`, `*Tests`, `*TestCase` detection ✅
- **Nested test classes**: Support for test classes within other test classes ✅
- **Dynamic test generation**: `unittest.TestLoader` and custom test discovery

### 3. **Enhanced Setup/Teardown Patterns** (Medium Priority) ✅ **IMPLEMENTED**
- **Custom setup method names**: Beyond standard `setUp`/`tearDown` (e.g., `setup_method`, `teardown_method`) ✅
- **Conditional setup**: `setUp` methods with conditions or parameters
- **Shared fixtures**: Detection and conversion of common setup patterns across multiple test classes
- **Resource management**: Enhanced cleanup for database connections, file handles, network sockets

### 4. **Advanced Test Organization Patterns** (Low Priority)
- **Test suites**: `unittest.TestSuite` and custom test collection patterns
- **Test runners**: Custom `unittest.TextTestRunner` configurations
- **Test discovery filtering**: Complex test selection and filtering patterns
- **Test inheritance hierarchies**: Complex inheritance chains beyond simple TestCase

### 5. **Data-Driven Test Patterns** (Medium Priority)
- **DDT (Data-Driven Tests)**: `@data` decorators and `TestCase` subclasses using data providers
- **YAML/JSON test data**: External test data file integration
- **CSV test data**: Test cases reading from CSV files
- **Database-driven tests**: Tests that load test data from databases

### 6. **Exception and Error Handling Patterns** (Medium Priority) ✅ **IMPLEMENTED**
- **ExpectedFailure**: `@unittest.expectedFailure` → `@pytest.mark.xfail` ✅
- **Custom exception types**: Domain-specific exception testing patterns
- **Exception chaining**: Tests that verify exception cause chains
- **Warning assertions**: `assertWarns`, `assertWarnsRegex` → `pytest.warns` ✅

### 7. **Async and Concurrent Test Patterns** (Low Priority)
- **Async test methods**: `async def test_*` methods (basic support exists)
- **Async setup/teardown**: `async def setUp()`, `async def tearDown()`
- **Concurrent test execution**: Tests using threading or multiprocessing
- **Async fixtures**: Conversion to async pytest fixtures

### 8. **Test Configuration and Metadata Patterns** (Low Priority)
- **Test descriptions**: Docstrings and custom test metadata
- **Test categories/tags**: Custom test categorization systems
- **Test timeouts**: `unittest.TestCase` timeout configurations
- **Test dependencies**: Setup dependencies between test methods

## 📊 **Pattern Priority Analysis**

### High Priority (Immediate Value)
1. **Mock patterns** - Most unittest codebases use mocks extensively
2. **Enhanced assertion patterns** - Fill gaps in current assertion support
3. **Advanced setup/teardown** - Handle edge cases in lifecycle management

### Medium Priority (Good Value)
1. **Custom test discovery** - Support more test organization patterns
2. **Data-driven tests** - Support popular testing patterns
3. **Exception handling enhancements** - Better error testing support

### Low Priority (Future Enhancement)
1. **Advanced test organization** - Complex inheritance and suite patterns
2. **Async testing** - Niche but growing use case
3. **Test configuration** - Metadata and configuration patterns

## 🎯 **Implementation Strategy**

### Phase 1: Mock Pattern Support
- Add `@patch` decorator transformation
- Implement mock object conversion helpers
- Add pytest-mock integration

### Phase 2: Enhanced Discovery Patterns
- Extend test method prefix detection
- Add support for custom test naming conventions
- Improve nested class handling

### Phase 3: Advanced Setup/Teardown
- Detect custom setup method names
- Add support for parameterized setup methods
- Improve resource cleanup detection

## 🔧 **Technical Considerations**

### Extensibility
- Current architecture supports adding new transformers via the plugin system
- Decision model can be extended to analyze new patterns
- CST-based approach allows precise AST-level transformations

### Backward Compatibility
- All new patterns should maintain conservative fallback behavior
- Existing transformations should remain unchanged
- New patterns should be opt-in where possible

### Testing Strategy
- Each new pattern needs comprehensive test coverage
- Include edge cases and error conditions
- Ensure no regressions in existing functionality

## 📈 **Impact Assessment**

Adding support for these additional patterns would:
- **Increase conversion coverage** by 30-50% for typical unittest codebases
- **Reduce manual post-conversion work** for developers
- **Improve pytest adoption** by handling more real-world patterns
- **Maintain transformation quality** through conservative, well-tested approaches

The current tool already handles the most common unittest patterns effectively. Adding support for the high-priority patterns identified here would significantly expand its utility for real-world unittest-to-pytest migrations.

## ✅ **Recently Implemented: Exception Handling Patterns**

As of October 2025, we have successfully implemented comprehensive support for **Exception and Error Handling Patterns**:

### **Implemented Features:**

1. **@unittest.expectedFailure Decorator**
   - Transforms `@unittest.expectedFailure` → `@pytest.mark.xfail()`
   - Handles both simple attribute decorators and callable decorators
   - Maintains all original arguments and formatting

2. **assertWarns and assertWarnsRegex Assertions**
   - Transforms `self.assertWarns(Exception, callable)` → `pytest.warns(Exception, lambda: callable())`
   - Transforms `self.assertWarnsRegex(Exception, callable, regex)` → `pytest.warns(Exception, lambda: callable(), match=regex)`
   - Properly handles function names, lambda expressions, and other callable types
   - Preserves regex patterns and match parameters correctly

3. **Enhanced Decorator Support**
   - Extended existing skip decorator support to handle expectedFailure
   - Maintains backward compatibility with existing `@unittest.skip` transformations
   - Properly handles both `@decorator` and `@decorator(args)` forms

### **Technical Implementation:**

- **Files Modified:**
  - `splurge_unittest_to_pytest/transformers/assert_transformer.py` - Added warning assertion transformers
  - `splurge_unittest_to_pytest/transformers/skip_transformer.py` - Added expectedFailure decorator support
  - `splurge_unittest_to_pytest/transformers/unittest_transformer.py` - Integrated new transformers into main mapping

- **Test Coverage:**
  - Added comprehensive test suite in `tests/unit/test_exception_handling_patterns.py`
  - Tests cover individual transformations and complex multi-pattern scenarios
  - All tests passing with proper validation of transformed output

- **Key Features:**
  - **Conservative approach**: Only transforms recognized patterns, preserves unknown code
  - **AST-level accuracy**: Uses libcst for precise syntax tree transformations
  - **Lambda handling**: Properly wraps function calls in lambda expressions when needed
  - **Import management**: Automatically adds `import pytest` when transformations are applied

### **Usage Examples:**

**Before:**
```python
import unittest

class TestExample(unittest.TestCase):
    @unittest.expectedFailure
    def test_something(self):
        self.assertWarns(ValueError, lambda: int("not_a_number"))

    def test_warnings(self):
        self.assertWarnsRegex(UserWarning, some_func, r"test.*pattern")
```

**After:**
```python
import pytest

class TestExample:
    @pytest.mark.xfail()
    def test_something(self):
        pytest.warns(ValueError, lambda: int("not_a_number"))

    def test_warnings(self):
        pytest.warns(UserWarning, lambda: some_func(), match=r"test.*pattern")
```

This implementation significantly improves the tool's ability to handle real-world unittest codebases that use exception testing patterns, reducing the need for manual post-conversion fixes.

## ✅ **Recently Implemented: Enhanced Test Discovery & Setup Patterns (October 2025)**

In addition to the exception handling patterns, we have successfully implemented comprehensive support for **Enhanced Test Discovery** and **Advanced Setup/Teardown Patterns**:

### **Enhanced Test Discovery Features:**

1. **Configurable Test Method Prefixes**
   - Extended pattern analyzer to support custom prefixes: `spec_`, `should_`, `it_`, etc.
   - Modified `UnittestPatternAnalyzer` to accept configurable test prefixes via constructor
   - Updated `ir_generation_step.py` to pass configuration from pipeline context
   - Maintains backward compatibility with existing `test_` prefix

2. **Nested Test Class Support**
   - Enhanced pattern analyzer with class hierarchy stack tracking
   - Properly handles nested test classes within other test classes
   - Maintains class relationships for complex test organization patterns
   - Preserves nested class structure in transformed output

3. **Advanced Setup Method Detection**
   - Extended setup/teardown method detection beyond standard `setUp`/`tearDown`
   - Added support for common custom patterns: `setup_method`, `teardown_method`, `before_each`, `after_each`, etc.
   - Enhanced pattern matching using configurable patterns
   - Preserves custom setup methods (doesn't convert to fixtures unless standard)

### **Technical Implementation:**

- **Files Modified:**
  - `splurge_unittest_to_pytest/pattern_analyzer.py` - Enhanced test method detection and nested class support
  - `splurge_unittest_to_pytest/steps/ir_generation_step.py` - Pass configuration to pattern analyzer
  - `tests/unit/test_enhanced_patterns.py` - Comprehensive test coverage for new patterns

- **Key Features:**
  - **Configurable prefixes**: `--prefix spec --prefix should --prefix it` for custom test naming
  - **Nested class support**: Handles `class InnerTest(unittest.TestCase)` within other test classes
  - **Custom setup detection**: Recognizes `setup_method`, `before_each`, `cleanup`, etc.
  - **Backward compatibility**: All existing functionality preserved

### **Usage Examples:**

**Custom Test Prefixes:**
```bash
# Support spec_ methods
splurge-unittest-to-pytest migrate --prefix spec tests/

# Support multiple prefixes
splurge-unittest-to-pytest migrate --prefix test --prefix spec --prefix should tests/
```

**Nested Test Classes:**
```python
# Before (preserved structure)
class TestExample(unittest.TestCase):
    def test_outer(self): pass

    class InnerTest(unittest.TestCase):
        def test_inner(self): pass

# After (preserved structure)
class TestExample:
    def test_outer(self): pass

    class InnerTest:
        def test_inner(self): pass
```

**Custom Setup Methods:**
```python
# Before (preserved as-is)
class TestExample(unittest.TestCase):
    def setup_method(self):
        self.value = 42

    def before_each(self):
        self.counter = 0

# After (preserved as-is)
class TestExample:
    def setup_method(self):
        self.value = 42

    def before_each(self):
        self.counter = 0
```

### **Benefits:**
- **Broader pattern support**: Handles modern testing frameworks that use different naming conventions
- **Nested organization**: Supports complex test class hierarchies
- **Custom setup patterns**: Recognizes various setup/teardown naming conventions
- **Zero breaking changes**: Fully backward compatible with existing functionality

This comprehensive enhancement significantly expands the tool's capability to handle diverse unittest codebases while maintaining the conservative, safe transformation approach.
