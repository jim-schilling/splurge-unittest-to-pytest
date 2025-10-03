# This file contains unittest in comments and docstrings
# import unittest - this is just a comment
# unittest.TestCase - also just a comment

"""
This is a docstring that mentions:
- self.assertEqual(a, b)
- self.assertTrue(condition)
- import unittest
"""


def some_function():
    """This function asserts something but not unittest asserts."""
    assert True  # This is a regular assert, not unittest
    return "not a test file"
