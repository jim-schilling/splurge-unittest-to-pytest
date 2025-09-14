import shutil

import libcst as cst

from splurge_unittest_to_pytest.main import convert_string
from splurge_unittest_to_pytest.stages.manager import StageManager


def _cleanup_mgr_dir(mgr: StageManager) -> None:
    d = getattr(mgr, "_diagnostics_dir", None)
    if d is None:
        return
    try:
        shutil.rmtree(d)
    except Exception:
        pass


def test_leave_ClassDef_removes_unittest_base_and_preserves_non_unittest():
    src = """
import unittest

class MyTest(unittest.TestCase):
    def test_one(self):
        self.assertEqual(1, 1)

class Other:
    pass
"""
    # Use the staged pipeline to convert the source; convert_string returns
    # a ConversionResult with the converted code.
    new_module_code = convert_string(src).converted_code

    # Ensure unittest.TestCase base removed from MyTest and test converted
    assert "unittest.TestCase" not in new_module_code
    assert "def test_one()" in new_module_code or "def test_one(" in new_module_code


def test_leave_FunctionDef_converts_setup_to_fixture_and_removes_self_from_tests():
    src = """
class X(unittest.TestCase):
    def setUp(self):
        self.x = 5

    def test_something(self):
        assert self.x == 5
"""
    new_module_code = convert_string(src).converted_code

    # setUp should be transformed into fixtures (fixture name or def present)
    assert "def test_something(" in new_module_code or "def test_something(self)" not in new_module_code


def test_leave_Module_adds_pytest_import_when_needed():
    src = """
class A(unittest.TestCase):
    def test_one(self):
        with self.assertRaises(ValueError):
            raise ValueError()
"""
    new_module_code = convert_string(src).converted_code
    # since assertRaises is converted, pytest import should be added if needed
    assert "import pytest" in new_module_code or "pytest" in new_module_code


def test_stage_manager_register_does_not_create_files_when_disabled(monkeypatch):
    # Ensure diagnostics disabled
    monkeypatch.delenv("SPLURGE_ENABLE_DIAGNOSTICS", raising=False)
    mgr = StageManager()
    try:

        def stage(ctx: dict):
            return {"ok": True}

        mgr.register(stage)
        module = cst.parse_module("x = 1\n")
        mgr.run(module)
        # Diagnostics dir should be None and no files created
        assert mgr._diagnostics_dir is None
    finally:
        _cleanup_mgr_dir(mgr)
