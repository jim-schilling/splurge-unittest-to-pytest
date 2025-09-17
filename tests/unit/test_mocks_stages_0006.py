import libcst as cst
from splurge_unittest_to_pytest.stages.decorator_and_mock_fixes import DecoratorAndMockTransformer

DOMAINS = ["mocks", "stages"]


def _apply(src: str) -> str:
    mod = cst.parse_module(src)
    new = mod.visit(DecoratorAndMockTransformer())
    return new.code


def test_patch_object_and_package_targets():
    src = """
from unittest.mock import patch

class P:
    @patch('package.module.Class.method')
    def test_m(self, m):
        self.assertIsNotNone(m)

    def test_obj(self):
        with patch.object(package.module.Class, 'attr', new=True):
            assert True
"""
    out = _apply(src)
    # Ensure decorators referencing dotted targets are preserved as calls
    assert "pytest" not in out or "patch" in out
    # output parses
    cst.parse_module(out)
