import unittest


class TestExample(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(1 + 1, 2)


if __name__ == "__main__":
    unittest.main()
