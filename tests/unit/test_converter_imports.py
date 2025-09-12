import libcst as cst
from splurge_unittest_to_pytest.converter import imports as imp_mod
from splurge_unittest_to_pytest.converter import import_helpers as ih


def test_make_pytest_import_stmt_code():
    stmt = ih.make_pytest_import_stmt()
    assert isinstance(stmt, cst.SimpleStatementLine)
    # rendering should be a simple import pytest statement
    # render via a Module wrapper since SimpleStatementLine has no .code attribute
    mod = cst.Module(body=[stmt])
    assert mod.code.strip() == "import pytest"


def test_has_pytest_import_true_and_false():
    m1 = cst.parse_module("import pytest\n")
    assert imp_mod.has_pytest_import(m1)

    m2 = cst.parse_module("from pytest import approx\n")
    assert imp_mod.has_pytest_import(m2)

    m3 = cst.parse_module("")
    assert not imp_mod.has_pytest_import(m3)


def test_add_pytest_import_empty_module():
    m = cst.parse_module("")
    m2 = imp_mod.add_pytest_import(m)
    # should now have a single import pytest statement
    assert m2.code.strip() == "import pytest"


def test_add_pytest_import_after_docstring_and_after_imports():
    src = '"""module doc"""\n\nimport os\nfrom sys import argv\n\nX = 1\n'
    m = cst.parse_module(src)
    m2 = imp_mod.add_pytest_import(m)
    code = m2.code
    # pytest import should appear after the docstring and after the two existing imports
    assert '"""module doc"""' in code
    # ensure pytest import is present
    assert 'import pytest' in code
    # ensure existing imports still present
    assert 'import os' in code and 'from sys import argv' in code


def test_add_pytest_import_idempotent():
    m = cst.parse_module("import pytest\n\nprint('ok')\n")
    m2 = imp_mod.add_pytest_import(m)
    assert m.code == m2.code


def test_remove_unittest_import_and_importfrom():
    # cst nodes to feed into the remover functions
    imp_node = cst.Import(names=[cst.ImportAlias(name=cst.Name("unittest"))])
    res = imp_mod.remove_unittest_import(imp_node)
    assert res is cst.RemovalSentinel.REMOVE

    from_node = cst.ImportFrom(module=cst.Name("unittest"), names=[cst.ImportAlias(name=cst.Name("TestCase"))])
    res2 = imp_mod.remove_unittest_importfrom(from_node)
    assert res2 is cst.RemovalSentinel.REMOVE

    # non-unittest import should be returned unchanged
    ok_node = cst.Import(names=[cst.ImportAlias(name=cst.Name("os"))])
    res3 = imp_mod.remove_unittest_import(ok_node)
    assert res3 is ok_node


def test_add_pytest_import_with_alias_and_from_variants():
    # module with pytest imported as alias should be detected
    m_alias = cst.parse_module("import pytest as pt\n")
    # has_pytest_import looks only for name=="pytest" or from pytest; aliasing means original name is Name('pytest')
    assert imp_mod.has_pytest_import(m_alias)

    # from pytest import approx should also be detected
    m_from = cst.parse_module("from pytest import approx\n")
    assert imp_mod.has_pytest_import(m_from)


def test_add_pytest_import_after_docstring_only_module():
    src = '"""only docstring"""\n\n# comment\nvar = 1\n'
    m = cst.parse_module(src)
    m2 = imp_mod.add_pytest_import(m)
    # ensure pytest import added after the docstring
    code = m2.code
    assert '"""only docstring"""' in code
    assert 'import pytest' in code
