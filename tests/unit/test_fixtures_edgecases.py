from splurge_unittest_to_pytest.main import convert_string


def test_fixture_with_multiple_cleanup_statements() -> None:
    src = '''
import unittest

class TestC(unittest.TestCase):
    def setUp(self) -> None:
        self.d = tempfile.mkdtemp()
        self.f = open(os.path.join(self.d, 'x'), 'w')

    def tearDown(self) -> None:
        self.f.close()
        shutil.rmtree(self.d, ignore_errors=True)

    def test_use(self) -> None:
        self.assertTrue(True)
'''
    result = convert_string(src, engine="pipeline")
    assert result.has_changes
    out = result.converted_code
    # Expect fixtures for d and f and cleanup present
    assert "def d():" in out or "def _d_value()" in out
    assert "rmtree" in out or "close(" in out


def test_complex_teardown_pattern() -> None:
    src = '''
import unittest

class TestD(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Something()

    def tearDown(self) -> None:
        if self.tmp:
            self.tmp.cleanup()

    def test_it(self) -> None:
        self.assertIsNotNone(self.tmp)
'''
    result = convert_string(src, engine="pipeline")
    assert result.has_changes
    out = result.converted_code
    # Ensure cleanup conditional is present in converted fixture
    assert "if" in out and "cleanup" in out
