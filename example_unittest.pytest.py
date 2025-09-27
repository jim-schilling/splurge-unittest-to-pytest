import pytest


class TestExample:
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.value = 42
        yield
        self.value = None

    def test_addition(self):
        """Test basic addition functionality."""
        result = 1 + 1
        assert result == 2
        assert result > 0

    def test_string_operations(self):
        """Test string operations."""
        text = "hello world"
        assert "hello" in text
        assert len(text) == 11


if __name__ == "__main__":
    pytest.main()
