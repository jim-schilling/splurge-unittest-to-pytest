"""Tests for stages.fixture_injector fixture insertion behavior."""

from __future__ import annotations

import libcst as cst

from splurge_unittest_to_pytest.stages import fixture_injector


def make_simple_fixture(name: str) -> cst.FunctionDef:
    return cst.FunctionDef(
        name=cst.Name(name),
        params=cst.Parameters(),
        body=cst.IndentedBlock(body=[cst.SimpleStatementLine(body=[cst.Pass()])]),
    )


def test_find_insertion_index_prefers_pytest_import():
    # module with pytest import
    mod = cst.parse_module("import os\nimport pytest\n\n# rest\n")
    # use the public stage to insert a fixture and assert the fixture
    # ends up after the pytest import (observable behavior)
    fn = make_simple_fixture("fix_a")
    out = fixture_injector.fixture_injector_stage({"module": mod, "fixture_nodes": [fn]})
    new_mod = out["module"]
    src = new_mod.code
    assert src.find("import pytest") != -1
    assert src.find("import pytest") < src.find("def fix_a")


def test_find_insertion_index_after_docstring_and_imports():
    mod = cst.parse_module('"doc"\nimport os\nfrom sys import path\n\nclass X: pass\n')
    fn = make_simple_fixture("fix_a")
    out = fixture_injector.fixture_injector_stage({"module": mod, "fixture_nodes": [fn]})
    new_mod = out["module"]
    src = new_mod.code
    # fixture must appear after the last import
    assert src.find("from sys import path") != -1
    assert src.find("from sys import path") < src.find("def fix_a")


def test_fixture_injector_inserts_fixtures_and_signals_pytest(tmp_path):
    mod = cst.parse_module("import os\n\n# end\n")
    fn1 = make_simple_fixture("fix_a")
    fn2 = make_simple_fixture("fix_b")

    ctx = {"module": mod, "fixture_nodes": [fn1, fn2]}
    out = fixture_injector.fixture_injector_stage(ctx)
    assert out["needs_pytest_import"] is True
    new_mod = out["module"]
    src = new_mod.code

    # should contain the fixture names and two blank-line sentinels (as \n\n)
    assert "def fix_a" in src
    assert "def fix_b" in src
    # ensure there are blank lines between top-level defs (simplistic check)
    assert "\n\ndef fix_a" in src or "\n\n\ndef fix_a" in src


def test_fixture_injector_no_module_or_no_nodes_returns_original():
    assert fixture_injector.fixture_injector_stage({}) == {"module": None}
