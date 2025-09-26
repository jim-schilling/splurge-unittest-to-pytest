import unittest


class TestExample(unittest.TestCase):
    def setUp(self):
        self.value = 42

    def tearDown(self):
        pass

    def test_something(self):
        self.assertEqual(self.value, 42)


if __name__ == "__main__":
    unittest.main()
