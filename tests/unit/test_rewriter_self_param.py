from splurge_unittest_to_pytest import main


def test_rewriter_ensures_self_with_fixture():
    src = """
import unittest

class TestDB(unittest.TestCase):
    def setUp(self):
        self.conn = setup_db()

    def test_action(self):
        self.assertTrue(True)
"""
    res = main.convert_string(src, engine='pipeline')
    assert 'def test_action(self' in res.converted_code
