import json
from pathlib import Path

import libcst as cst

from splurge_unittest_to_pytest.stages.decorator_and_mock_fixes import DecoratorAndMockTransformer


def _apply_transform(src: str) -> str:
    mod = cst.parse_module(src)
    new = mod.visit(DecoratorAndMockTransformer())
    return new.code


def test_mock_import_rewrite():
    src = "from unittest.mock import patch, MagicMock, side_effect\n"
    out = _apply_transform(src)
    assert "import unittest.mock as mock" in out
    assert "side_effect" not in out.splitlines()[0]


def test_unittest_decorator_to_pytest_mark():
    src = (
        "@unittest.skip('reason')\ndef test_foo():\n    pass\n\n@unittest.expectedFailure\ndef test_bar():\n    pass\n"
    )
    out = _apply_transform(src)
    assert "pytest.mark.skip" in out
    assert "pytest.mark.xfail" in out


def test_skipif_and_skipunless_and_name_variants():
    src = "@unittest.skipIf(True, 'nope')\ndef test_a():\n    pass\n\n@unittest.skipUnless(False, reason='why')\ndef test_b():\n    pass\n\n@expectedFailure\ndef test_c():\n    pass\n"
    out = _apply_transform(src)
    assert "pytest.mark.skipif" in out
    assert "reason='why'" in out or "reason =" in out
    assert "pytest.mark.xfail" in out


def test_mock_import_alias_and_multiline():
    src = "from unittest.mock import (\n    patch as p,\n    MagicMock,\n    side_effect,\n)\n"
    out = _apply_transform(src)
    assert "import unittest.mock as mock" in out
    assert "patch" in out


def _apply(src: str) -> str:
    mod = cst.parse_module(src)
    new = mod.visit(DecoratorAndMockTransformer())
    return new.code


def test_decorator_factory_expected_and_skip():
    src = "\nimport unittest\n\ndef deco(x):\n    def _d(fn):\n        return fn\n    return _d\n\nclass T(unittest.TestCase):\n    @deco(1)\n    @unittest.expectedFailure\n    def test_a(self):\n        assert 1 == 2\n\n    @deco(0)\n    @unittest.skip('skip it')\n    def test_b(self):\n        assert False\n"
    out = _apply(src)
    assert "pytest.mark.xfail" in out
    assert "pytest.mark.skip" in out


def test_known_bad_mapping_loaded():
    p = Path(__file__).parents[2] / "splurge_unittest_to_pytest" / "data" / "known_bad_mock_names.json"
    assert p.exists(), "known_bad_mock_names.json must exist"
    parsed = json.loads(p.read_text(encoding="utf8"))
    assert isinstance(parsed, dict)
    assert "side_effect" in parsed, "mapping should include 'side_effect'"


def test_transformer_rewrites_side_effect_import():
    src = "from unittest.mock import patch, MagicMock, side_effect\n"
    module = cst.parse_module(src)
    tr = DecoratorAndMockTransformer()
    new_mod = module.visit(tr)
    code = new_mod.code
    assert "side_effect" not in code.splitlines()[0]
    assert any(("import unittest.mock as mock" in line for line in code.splitlines()))


def _apply__01(src: str) -> str:
    mod = cst.parse_module(src)
    new = mod.visit(DecoratorAndMockTransformer())
    return new.code


def test_mock_from_import_rewrite_with_autospec_and_side_effect():
    src = "\nfrom unittest.mock import Mock, autospec, side_effect, patch\n\nclass T:\n    def test(self):\n        m = Mock()\n        m.side_effect = lambda: None\n"
    out = _apply__01(src)
    assert "import unittest.mock as mock" in out or "from unittest.mock import Mock" in out
    assert "side_effect" not in out.splitlines()[0]


def _apply_transformer(src: str) -> str:
    mod = cst.parse_module(src)
    new = mod.visit(DecoratorAndMockTransformer())
    return new.code


def test_mock_star_and_aliases_remain_valid():
    src = "\nimport unittest\nfrom unittest.mock import *\nimport unittest.mock as m\nfrom unittest.mock import Mock as M, patch as p\n\nclass X(unittest.TestCase):\n    def test(self):\n        m = M()\n        self.assertIsNotNone(m)\n"
    out = _apply_transformer(src)
    cst.parse_module(out)
    assert (
        "from unittest.mock import *" in out
        or "import unittest.mock as mock" in out
        or "import unittest.mock as m" in out
    )


def _apply__02(src: str) -> str:
    mod = cst.parse_module(src)
    new = mod.visit(DecoratorAndMockTransformer())
    return new.code


def test_patch_object_and_package_targets():
    src = "\nfrom unittest.mock import patch\n\nclass P:\n    @patch('package.module.Class.method')\n    def test_m(self, m):\n        self.assertIsNotNone(m)\n\n    def test_obj(self):\n        with patch.object(package.module.Class, 'attr', new=True):\n            assert True\n"
    out = _apply__02(src)
    assert "pytest" not in out or "patch" in out
    cst.parse_module(out)
