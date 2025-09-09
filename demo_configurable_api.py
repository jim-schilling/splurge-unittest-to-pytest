#!/usr/bin/env python3
"""Demo script showing the new configurable method pattern API."""

from splurge_unittest_to_pytest.converter import UnittestToPytestTransformer

def main():
    """Demonstrate the configurable method pattern API."""
    print("=== Unittest to Pytest Converter - Configurable API Demo ===\n")

    # Create transformer instance
    transformer = UnittestToPytestTransformer()

    print("1. Default Patterns:")
    print(f"   Setup patterns: {sorted(transformer.setup_patterns)}")
    print(f"   Teardown patterns: {sorted(transformer.teardown_patterns)}")
    print(f"   Test patterns: {sorted(transformer.test_patterns)}")
    print()

    print("2. Adding Custom Patterns:")

    # Add custom setup patterns
    transformer.add_setup_pattern("before_all")
    transformer.add_setup_pattern("setup_class")
    print("   Added setup patterns: 'before_all', 'setup_class'")

    # Add custom teardown patterns
    transformer.add_teardown_pattern("after_all")
    transformer.add_teardown_pattern("teardown_class")
    print("   Added teardown patterns: 'after_all', 'teardown_class'")

    # Add custom test patterns
    transformer.add_test_pattern("describe_")
    transformer.add_test_pattern("context_")
    print("   Added test patterns: 'describe_', 'context_'")
    print()

    print("3. Updated Patterns:")
    print(f"   Setup patterns: {sorted(transformer.setup_patterns)}")
    print(f"   Teardown patterns: {sorted(transformer.teardown_patterns)}")
    print(f"   Test patterns: {sorted(transformer.test_patterns)}")
    print()

    print("4. Testing Pattern Recognition:")

    # Test setup method recognition
    test_methods = [
        "setUp", "before_all", "setup_class", "custom_setup",
        "tearDown", "after_all", "teardown_class", "custom_teardown",
        "test_example", "describe_feature", "context_scenario", "should_work"
    ]

    for method in test_methods:
        is_setup = transformer._is_setup_method(method)
        is_teardown = transformer._is_teardown_method(method)
        is_test = transformer._is_test_method(method)

        result = []
        if is_setup:
            result.append("SETUP")
        if is_teardown:
            result.append("TEARDOWN")
        if is_test:
            result.append("TEST")

        if result:
            print(f"   {method:<15} -> {', '.join(result)}")
        else:
            print(f"   {method:<15} -> Not recognized")

    print("\n=== Demo Complete ===")

if __name__ == "__main__":
    main()
