from splurge_unittest_to_pytest import main


def test_rewriter_ensures_self_with_fixture() -> None:
    src = """
import unittest

class TestDB(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = setup_db()

    def test_action(self) -> None:
        self.assertTrue(True)
"""
    res = main.convert_string(src, engine="pipeline")
    # Option A: methods are converted to plain pytest functions receiving fixtures
    assert "def test_action(conn" in res.converted_code
