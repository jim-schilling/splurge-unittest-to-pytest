from pathlib import Path

import libcst as cst

from splurge_unittest_to_pytest.main import convert_string


def _has_pytest_fixture(mod: cst.Module) -> bool:
    for stmt in mod.body:
        if isinstance(stmt, cst.FunctionDef):
            for dec in stmt.decorators:
                d = dec.decorator
                if isinstance(d, cst.Attribute) and isinstance(d.value, cst.Name) and d.value.value == "pytest":
                    if isinstance(d.attr, cst.Name) and d.attr.value == "fixture":
                        return True
    return False


def _find_test_defs(mod: cst.Module) -> list[cst.FunctionDef]:
    return [s for s in mod.body if isinstance(s, cst.FunctionDef) and s.name.value.startswith("test_")]


def _assert_structural(res_code: str) -> None:
    mod = cst.parse_module(res_code)
    if _has_pytest_fixture(mod):
        return
    tests = _find_test_defs(mod)
    assert tests, "No test functions found in converted module"
    for t in tests:
        assert len(t.params.params) == 1, f"Test {t.name.value} must accept a single fixture parameter"


def test_alias_functiontestcase_structural():
    src = """
import unittest
from unittest import FunctionTestCase
from mylibrary import createResource, deleteResource

_resource = None

def testSomething():
    something = makeSomething()
    assert something is not None

def initResource():
    _resource = createResource()

def cleanupResource():
    deleteResource(_resource)

tc = FunctionTestCase(testSomething, setUp=initResource, tearDown=cleanupResource)
"""
    res = convert_string(src, normalize_names=False)
    assert res.errors == []
    assert res.has_changes
    _assert_structural(res.converted_code)


def test_multiple_functiontestcases_structural():
    src = """
import unittest
from mylibrary import createResource, deleteResource

_resource1 = None
_resource2 = None

def testSomething():
    assert makeSomething() is not None

def init1():
    _resource1 = createResource()

def cleanup1():
    deleteResource(_resource1)

def testOther():
    assert makeOther() is not None

def init2():
    _resource2 = createResource()

def cleanup2():
    deleteResource(_resource2)

tc1 = unittest.FunctionTestCase(testSomething, setUp=init1, tearDown=cleanup1)
tc2 = unittest.FunctionTestCase(testOther, setUp=init2, tearDown=cleanup2)
"""
    res = convert_string(src, normalize_names=False)
    assert res.errors == []
    assert res.has_changes
    # expect two test functions each taking one fixture parameter or fixtures emitted
    mod = cst.parse_module(res.converted_code)
    tests = _find_test_defs(mod)
    assert len(tests) == 2
    for t in tests:
        assert len(t.params.params) == 1


def test_collision_scenario_structural():
    # Two setup helpers assign to names that canonicalization might collide on.
    src = """
import unittest
from mylibrary import createResource, deleteResource

_resource = None
resource = None

def testA():
    assert True

def initA():
    _resource = createResource()

def cleanupA():
    deleteResource(_resource)

def testB():
    assert True

def initB():
    resource = createResource()

def cleanupB():
    deleteResource(resource)

tc1 = unittest.FunctionTestCase(testA, setUp=initA, tearDown=cleanupA)
tc2 = unittest.FunctionTestCase(testB, setUp=initB, tearDown=cleanupB)
"""
    # Run with normalize_names True to exercise canonicalization path
    res = convert_string(src, normalize_names=True)
    assert res.errors == []
    assert res.has_changes
    # structural check: two tests each accept one fixture parameter or fixtures emitted
    _assert_structural(res.converted_code)


def test_alias_as_import_handling():
    src = """
import unittest
from unittest import FunctionTestCase as FTC
from mylibrary import createResource, deleteResource

_resource = None

def testSomething():
    something = makeSomething()
    assert something is not None

def initResource():
    _resource = createResource()

def cleanupResource():
    deleteResource(_resource)

tc = FTC(testSomething, setUp=initResource, tearDown=cleanupResource)
"""
    res = convert_string(src, normalize_names=False)
    assert res.errors == []
    assert res.has_changes
    _assert_structural(res.converted_code)


def test_normalize_names_false_and_true():
    src = Path("tests/data/unittest_pytest_samples/unittest_01_a.py.txt").read_text()
    res_false = convert_string(src, normalize_names=False)
    res_true = convert_string(src, normalize_names=True)
    # both should be structurally equivalent to golden (fixtures or single-param tests)
    _assert_structural(res_false.converted_code)
    _assert_structural(res_true.converted_code)
