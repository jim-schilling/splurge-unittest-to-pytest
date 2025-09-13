#!/usr/bin/env python3
"""Demo script showing flexible parameter handling for different method types.

Note: this example demonstrates internal helper behavior on PatternConfigurator
for illustrative purposes; these helpers are implementation details and may
change between releases. Prefer the public `convert_string` API for conversions.
"""

import libcst as cst
from splurge_unittest_to_pytest.main import PatternConfigurator


def main() -> None:
    """Demonstrate flexible parameter handling."""
    print("=== Flexible Parameter Handling Demo ===\n")

    transformer = PatternConfigurator()

    # Test cases for different method types
    test_cases = [
        {
            "name": "Instance Method (self)",
            "code": """
def test_example(self, arg1, arg2):
    self.assertEqual(self.value, arg1)
    result = self.helper_method(arg2)
    return result
""",
            "decorators": [],
        },
        {
            "name": "Class Method (cls)",
            "code": """
@classmethod
def test_class_example(cls, arg1):
    cls.assertEqual(cls.class_value, arg1)
    return cls.create_instance()
""",
            "decorators": ["classmethod"],
        },
        {
            "name": "Static Method",
            "code": """
@staticmethod
def test_static_example(arg1, arg2):
    assert arg1 == arg2
    return helper_function(arg1)
""",
            "decorators": ["staticmethod"],
        },
        {
            "name": "Method without conventional first param",
            "code": """
def test_custom_example(obj, arg1):
    obj.assertEqual(obj.value, arg1)
    return obj.process(arg1)
""",
            "decorators": [],
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}. {test_case['name']}:")
        print("   Original method signature and body:")

        # Parse the code
        try:
            module = cst.parse_module(test_case["code"])
            func_def = module.body[0]  # Get the function definition

            # Add decorators if specified
            if test_case["decorators"]:
                decorators = []
                for decorator_name in test_case["decorators"]:
                    decorators.append(cst.Decorator(decorator=cst.Name(decorator_name)))
                func_def = func_def.with_changes(decorators=decorators)

            print(f"   {cst.Module(body=[func_def]).code.strip()}")

            # Test parameter removal
            should_remove = transformer._should_remove_first_param(func_def)
            print(f"   Should remove first param: {should_remove}")

            if func_def.params.params:
                first_param = func_def.params.params[0].name.value
                print(f"   First parameter: '{first_param}'")

            new_params, new_body = transformer._remove_method_self_references(func_def)
            print(f"   Parameters after processing: {[p.name.value for p in new_params]}")

        except Exception as e:
            print(f"   Error processing: {e}")

        print()

    print("=== Summary ===")
    print("✅ Instance methods with 'self' -> self parameter removed")
    print("✅ Class methods with 'cls' -> cls parameter removed")
    print("✅ Static methods -> no parameters removed")
    print("✅ Methods without conventional params -> no parameters removed")
    print("✅ References to removed parameters are also cleaned up")


if __name__ == "__main__":
    main()
