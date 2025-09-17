from __future__ import annotations
import libcst as cst
from splurge_unittest_to_pytest.stages.collector import Collector

SAMPLE = "\nclass MyTests(unittest.TestCase):\n    def setUp(self) -> None:\n        self.resource = open('file.txt')\n        self.count = 42\n\n    def tearDown(self) -> None:\n        if self.resource is not None:\n            self.resource.close()\n\n    def test_one(self) -> None:\n        assert self.count == 42\n"


def test_collector_captures_setup_and_teardown() -> None:
    module = cst.parse_module(SAMPLE)
    visitor = Collector()
    module.visit(visitor)
    out = visitor.as_output()
    assert "MyTests" in out.classes
    cls = out.classes["MyTests"]
    assert "resource" in cls.setup_assignments
    assert "count" in cls.setup_assignments
    assert len(cls.teardown_statements) == 1
    stmt = cls.teardown_statements[0]
    assert isinstance(stmt, cst.If)
    assert out.has_unittest_usage is True
