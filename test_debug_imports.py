import libcst as cst

source_code = """import unittest
from pytest import fixture

TEST_DATA = [1, 2, 3]

@fixture
def sample_data():
    return "test"
"""

module = cst.parse_module(source_code)

print("=== Module level analysis ===")
for node in module.body:
    print(f"Top level node: {type(node).__name__}")
    if isinstance(node, cst.Import):
        print("  Found Import node")
        for alias in node.names:
            print(f"    Alias: {type(alias).__name__}")
            print(f"    Has name: {hasattr(alias, 'name')}")
            if hasattr(alias, "name") and alias.name:
                print(f"    Name value: {alias.name.value}")
    elif isinstance(node, cst.ImportFrom):
        print("  Found ImportFrom node")
        print(f"  Module: {node.module.value if node.module else 'None'}")
        for alias in node.names:
            print(f"    Alias: {type(alias).__name__}")
            if hasattr(alias, "name") and alias.name:
                print(f"    Name value: {alias.name.value}")
    elif isinstance(node, cst.Assign):
        print("  Found Assign node")
        for target in node.targets:
            print(f"    Target: {type(target.target).__name__}")
            if hasattr(target.target, "value"):
                print(f"    Target value: {target.target.value}")
    elif isinstance(node, cst.FunctionDef):
        print(f"  Found Function: {node.name.value}")
        for decorator in node.decorators:
            print(f"    Decorator: {type(decorator.decorator).__name__}")
