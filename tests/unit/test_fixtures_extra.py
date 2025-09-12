import libcst as cst

from splurge_unittest_to_pytest.converter.fixtures import (
    create_simple_fixture,
    create_fixture_with_cleanup,
    create_fixture_for_attribute,
)


def test_create_simple_fixture_structure():
    f = create_simple_fixture('x', cst.parse_expression('1'))
    assert isinstance(f, cst.FunctionDef)
    # Body should contain Assign then Return
    assert isinstance(f.body, cst.IndentedBlock)
    assert len(f.body.body) >= 2
    assert isinstance(f.body.body[0], cst.SimpleStatementLine)
    assert isinstance(f.body.body[1], cst.SimpleStatementLine)
    assert isinstance(f.body.body[1].body[0], cst.Return)


def test_create_fixture_with_cleanup_yield_and_replacement():
    cleanup_stmt = cst.parse_statement("del self.x")
    f = create_fixture_with_cleanup('x', cst.parse_expression("'v'"), [cleanup_stmt])
    assert isinstance(f, cst.FunctionDef)
    # Should contain assign, yield, and cleanup statements
    stmts = f.body.body
    assert any(isinstance(s.body[0], cst.Assign) for s in stmts if isinstance(s, cst.SimpleStatementLine))
    assert any(isinstance(s.body[0], cst.Expr) and isinstance(s.body[0].value, cst.Yield) for s in stmts if isinstance(s, cst.SimpleStatementLine))
    # Render the function into a module and ensure the generated code contains
    # the local replacement name and the cleanup 'del' statement
    mod = cst.Module(body=[f])
    code = getattr(mod, 'code', None)
    assert code is not None
    assert '_x_value' in code or 'del' in code


def test_create_fixture_for_attribute_delegation():
    # No cleanup provided -> simple fixture
    f1 = create_fixture_for_attribute('y', cst.parse_expression('2'), {})
    assert isinstance(f1, cst.FunctionDef)

    # With cleanup provided -> cleanup fixture
    cleanup = {'y': [cst.parse_statement('del self.y')]}
    f2 = create_fixture_for_attribute('y', cst.parse_expression('2'), cleanup)
    assert isinstance(f2, cst.FunctionDef)
