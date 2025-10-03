import unittest

# This file imports unittest but doesn't define any tests
# It just uses unittest utilities for some other purpose


def utility_function():
    # Maybe uses unittest.TestLoader or something
    loader = unittest.TestLoader()
    return loader


class RegularClass:
    def method(self):
        return "not a test"
