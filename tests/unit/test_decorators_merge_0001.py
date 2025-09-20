from typing import cast

import libcst as cst

from splurge_unittest_to_pytest.converter.decorators import build_pytest_fixture_decorator


def _render_decorator(dec: cst.Decorator) -> str:
    return cst.Module(
        body=[cst.SimpleStatementLine(body=[cst.Expr(value=cast(cst.BaseExpression, dec.decorator))])]
    ).code


def test_merge_mapping_and_explicit_kwargs():
    # mapping and explicit kwargs should be merged
    dec = build_pytest_fixture_decorator({"scope": "module"}, autouse=True)
    code = _render_decorator(dec)
    assert "pytest.fixture" in code and "autouse" in code and "module" in code


def test_explicit_kwargs_override_mapping():
    # explicit kwargs take precedence over mapping entries
    dec = build_pytest_fixture_decorator({"scope": "function", "autouse": False}, autouse=True)
    code = _render_decorator(dec)
    # autouse should be present and rendered True; scope should show 'function' or 'module' token present
    assert "autouse" in code and "True" in code


def test_exact_rendering_and_precedence():
    # Ensure explicit kwargs override mapping and rendering contains expected tokens
    dec = build_pytest_fixture_decorator({"scope": "function", "autouse": False}, autouse=True, scope="module")
    code = _render_decorator(dec).strip()
    # libcst currently renders kwargs as: autouse = True, scope = 'module'
    assert code.startswith("pytest.fixture(")
    assert "autouse" in code and "True" in code
    assert "scope" in code and "module" in code
    # Simple exact substring check for the common rendered form (spaces around '=')
    assert "autouse = True" in code and "scope = 'module'" in code
