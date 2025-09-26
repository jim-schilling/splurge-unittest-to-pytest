import pytest


class TestBasicMath:
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.calculator = Calculator()
        yield
        self.calculator = None

    def test_addition(self):
        result = self.calculator.add(2, 3)
        assert result == 5

    def test_subtraction(self):
        result = self.calculator.subtract(5, 3)
        assert result == 2


class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b
