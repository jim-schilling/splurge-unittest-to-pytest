"""Test the flexible parameter handling for different method types."""

import libcst as cst
from typing import cast
from splurge_unittest_to_pytest.stages.rewriter import rewriter_stage


class TestFlexibleParameterHandling:
    """Test that the `rewriter_stage` produces correct parameter lists."""

    def _make_class_module(self, func_def_src: str) -> str:
        return f"""
import unittest

class T(unittest.TestCase):
{func_def_src}
"""

    def _convert_and_get_params(self, src: str) -> list[str]:
        """Convert class source and return parameter name list."""
        mod = cst.parse_module(src)
        ctx = {'module': mod, 'collector_output': None}
        # For rewriter_stage we need a collector_output that provides classes map
        # Simulate collector output with empty setup_assignments for simplicity
        fake = type('F', (), {})()
        fake.classes = {'T': type('CI', (), {'setup_assignments': {}})()}
        ctx['collector_output'] = fake

        res = rewriter_stage(ctx)
        # res.get('module') may be typed as Any | None in test context — cast to Module
        new_mod = cast(cst.Module, res.get('module'))

        # find the FunctionDef and return its parameter names
        for node in new_mod.body:
            if isinstance(node, cst.ClassDef) and node.name.value == 'T':
                for item in node.body.body:
                    if isinstance(item, cst.FunctionDef):
                        return [p.name.value for p in item.params.params]
        return []

    def test_instance_method_inserts_self(self) -> None:
        src = '    def test_one(self, arg1):\n        pass\n'
        params = self._convert_and_get_params(self._make_class_module(src))
        assert params[0] in ('self',)

    def test_classmethod_inserts_cls(self) -> None:
        src = '    @classmethod\n    def test_one(cls, arg1):\n        pass\n'
        params = self._convert_and_get_params(self._make_class_module(src))
        assert params[0] == 'cls'

    def test_staticmethod_keeps_params(self) -> None:
        src = '    @staticmethod\n    def test_one(arg1, arg2):\n        pass\n'
        params = self._convert_and_get_params(self._make_class_module(src))
        assert params == ['arg1', 'arg2']
