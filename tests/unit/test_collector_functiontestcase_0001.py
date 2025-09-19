import libcst as cst

from splurge_unittest_to_pytest.stages.collector import Collector


def test_collector_detects_functiontestcase_sample():
    # Use a clean, syntactically-valid sample equivalent to the project's
    # FunctionTestCase sample to avoid parsing brittle test fixtures.
    src = """
import unittest
from mylibrary import createResource, deleteResource


_resource = None


def testSomething():
    something = makeSomething()
    assert something is not None


def initResource():
    global _resource
    _resource = createResource()


def cleanupResource():
    deleteResource(_resource)


testcase = unittest.FunctionTestCase(testSomething, setUp=initResource, tearDown=cleanupResource)
"""
    module = cst.parse_module(src)
    wrapper = cst.MetadataWrapper(module)
    visitor = Collector()
    wrapper.visit(visitor)
    out = visitor.as_output()
    # Expect at least one synthetic FunctionTestCase entry
    matches = [k for k in out.classes.keys() if k.startswith("FunctionTestCase_")]
    assert matches, "No FunctionTestCase synthetic class registered"
    synth = out.classes[matches[0]]
    # setup assignments should include the module-level resource name
    assert "_resource" in synth.setup_assignments
    # teardown statements should be present
    assert synth.teardown_statements
