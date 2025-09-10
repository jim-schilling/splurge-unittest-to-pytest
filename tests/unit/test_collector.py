from __future__ import annotations

import libcst as cst
from splurge_unittest_to_pytest.stages.collector import Collector


SAMPLE = """
class MyTests(unittest.TestCase):
    def setUp(self):
        self.resource = open('file.txt')
        self.count = 42

    def tearDown(self):
        if self.resource is not None:
            self.resource.close()

    def test_one(self):
        assert self.count == 42
"""


def test_collector_captures_setup_and_teardown():
    module = cst.parse_module(SAMPLE)
    visitor = Collector()
    module.visit(visitor)
    out = visitor.as_output()

    assert 'MyTests' in out.classes
    cls = out.classes['MyTests']
    assert 'resource' in cls.setup_assignments
    assert 'count' in cls.setup_assignments
    # teardown statements captured
    assert len(cls.teardown_statements) == 1
    stmt = cls.teardown_statements[0]
    # should be an if statement in teardown
    assert isinstance(stmt, cst.If)
    # has_unittest_usage should be True because we saw self.resource assignment
    assert out.has_unittest_usage is True
