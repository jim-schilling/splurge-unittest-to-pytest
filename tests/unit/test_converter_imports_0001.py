import libcst as cst
from splurge_unittest_to_pytest.converter.imports import add_pytest_import, has_pytest_import
from splurge_unittest_to_pytest.converter import imports as conv_imports
from splurge_unittest_to_pytest.converter import import_helpers as ih
from splurge_unittest_to_pytest.converter import imports


def test_add_pytest_import_inserts_after_docstring():
    src = '"""module doc"""\n\n'
    module = cst.parse_module(src)
    new_module = add_pytest_import(module)
    assert has_pytest_import(new_module)


def test_add_pytest_import_after_existing_imports():
    src = "import os\nimport sys\n"
    module = cst.parse_module(src)
    new_module = add_pytest_import(module)
    assert has_pytest_import(new_module)


def test_remove_unittest_importfrom_removes():
    stmt = cst.parse_statement("from unittest import TestCase")
    impfrom = stmt.body[0]
    res = conv_imports.remove_unittest_importfrom(impfrom)
    assert res is cst.RemovalSentinel.REMOVE


def test_remove_unittest_import_keeps_other():
    import libcst as cst
    from splurge_unittest_to_pytest.converter import imports as conv_imports
    from splurge_unittest_to_pytest.converter import import_helpers as ih

    def test_remove_unittest_importfrom_removes():
        stmt = cst.parse_statement("from unittest import TestCase")
        impfrom = stmt.body[0]
        res = conv_imports.remove_unittest_importfrom(impfrom)
        assert res is cst.RemovalSentinel.REMOVE

    def test_remove_unittest_import_keeps_other():
        stmt = cst.parse_statement("import os")
        imp = stmt.body[0]
        res = conv_imports.remove_unittest_import(imp)
        assert isinstance(res, cst.Import)

    def test_remove_unittest_import_removes_unittest_alias():
        stmt = cst.parse_statement("import unittest, os")
        imp = stmt.body[0]
        res = conv_imports.remove_unittest_import(imp)
        assert res is cst.RemovalSentinel.REMOVE

    def test_has_pytest_import_true_for_import():
        mod = cst.parse_module("import pytest\n")
        assert conv_imports.has_pytest_import(mod) is True

    def test_has_pytest_import_true_for_importfrom():
        mod = cst.parse_module("from pytest import raises\n")
        assert conv_imports.has_pytest_import(mod) is True

    def test_has_pytest_import_false():
        mod = cst.parse_module("import os\n")
        assert conv_imports.has_pytest_import(mod) is False

    def test_add_pytest_import_inserts_after_docstring_and_imports():
        src = '"""doc"""\n\nimport os\n\nx = 1\n'
        mod = cst.parse_module(src)
        new = conv_imports.add_pytest_import(mod)
        code = new.code
        assert code.count("import pytest") == 1
        assert code.index('"""doc"""') < code.index("import os")
        assert code.index("import os") < code.index("import pytest")
        assert code.index("import pytest") < code.index("x = 1")

    def test_add_pytest_import_no_duplicate():
        src = "import pytest\nimport os\n"
        mod = cst.parse_module(src)
        new = conv_imports.add_pytest_import(mod)
        assert new.code.count("import pytest") == 1

    def test_add_pytest_import_in_top_when_no_imports():
        src = "x = 1\n"
        mod = cst.parse_module(src)
        new = conv_imports.add_pytest_import(mod)
        code = new.code
        assert code.index("import pytest") < code.index("x = 1")

    def test_make_pytest_import_stmt_code():
        stmt = ih.make_pytest_import_stmt()
        assert isinstance(stmt, cst.SimpleStatementLine)
        mod = cst.Module(body=[stmt])
        assert mod.code.strip() == "import pytest"

    def test_has_pytest_import_true_and_false():
        m1 = cst.parse_module("import pytest\n")
        assert conv_imports.has_pytest_import(m1)
        m2 = cst.parse_module("from pytest import approx\n")
        assert conv_imports.has_pytest_import(m2)
        m3 = cst.parse_module("")
        assert not conv_imports.has_pytest_import(m3)

    def test_add_pytest_import_empty_module():
        m = cst.parse_module("")
        m2 = conv_imports.add_pytest_import(m)
        assert m2.code.strip() == "import pytest"

    def test_add_pytest_import_after_docstring_and_after_imports():
        src = '"""module doc"""\n\nimport os\nfrom sys import argv\n\nX = 1\n'
        m = cst.parse_module(src)
        m2 = conv_imports.add_pytest_import(m)
        code = m2.code
        assert '"""module doc"""' in code
        assert "import pytest" in code
        assert "import os" in code and "from sys import argv" in code

    def test_add_pytest_import_idempotent():
        m = cst.parse_module("import pytest\n\nprint('ok')\n")
        m2 = conv_imports.add_pytest_import(m)
        assert m.code == m2.code

    def test_remove_unittest_import_and_importfrom():
        imp_node = cst.Import(names=[cst.ImportAlias(name=cst.Name("unittest"))])
        res = conv_imports.remove_unittest_import(imp_node)
        assert res is cst.RemovalSentinel.REMOVE
        from_node = cst.ImportFrom(module=cst.Name("unittest"), names=[cst.ImportAlias(name=cst.Name("TestCase"))])
        res2 = conv_imports.remove_unittest_importfrom(from_node)
        assert res2 is cst.RemovalSentinel.REMOVE
        ok_node = cst.Import(names=[cst.ImportAlias(name=cst.Name("os"))])
        res3 = conv_imports.remove_unittest_import(ok_node)
        assert res3 is ok_node

    def test_add_pytest_import_with_alias_and_from_variants():
        m_alias = cst.parse_module("import pytest as pt\n")
        assert conv_imports.has_pytest_import(m_alias)
        m_from = cst.parse_module("from pytest import approx\n")
        assert conv_imports.has_pytest_import(m_from)

    def test_add_pytest_import_after_docstring_only_module():
        src = '"""only docstring"""\n\n# comment\nvar = 1\n'
        m = cst.parse_module(src)
        m2 = conv_imports.add_pytest_import(m)
        code = m2.code
        assert '"""only docstring"""' in code
        assert "import pytest" in code


def test_remove_unittest_import_removes_unittest_alias():
    stmt = cst.parse_statement("import unittest, os")
    imp = stmt.body[0]
    res = conv_imports.remove_unittest_import(imp)
    assert res is cst.RemovalSentinel.REMOVE


def test_has_pytest_import_true_for_import():
    mod = cst.parse_module("import pytest\n")
    assert conv_imports.has_pytest_import(mod) is True


def test_has_pytest_import_true_for_importfrom():
    mod = cst.parse_module("from pytest import raises\n")
    assert conv_imports.has_pytest_import(mod) is True


def test_has_pytest_import_false():
    mod = cst.parse_module("import os\n")
    assert conv_imports.has_pytest_import(mod) is False


def test_add_pytest_import_inserts_after_docstring_and_imports():
    src = '"""doc"""\n\nimport os\n\nx = 1\n'
    mod = cst.parse_module(src)
    new = conv_imports.add_pytest_import(mod)
    code = new.code
    assert code.count("import pytest") == 1
    assert code.index('"""doc"""') < code.index("import os")
    assert code.index("import os") < code.index("import pytest")
    assert code.index("import pytest") < code.index("x = 1")


def test_add_pytest_import_no_duplicate():
    src = "import pytest\nimport os\n"
    mod = cst.parse_module(src)
    new = conv_imports.add_pytest_import(mod)
    assert new.code.count("import pytest") == 1


def test_add_pytest_import_in_top_when_no_imports():
    src = "x = 1\n"
    mod = cst.parse_module(src)
    new = conv_imports.add_pytest_import(mod)
    code = new.code
    assert code.index("import pytest") < code.index("x = 1")


def test_make_pytest_import_stmt_code():
    stmt = ih.make_pytest_import_stmt()
    assert isinstance(stmt, cst.SimpleStatementLine)
    mod = cst.Module(body=[stmt])
    assert mod.code.strip() == "import pytest"


def test_has_pytest_import_true_and_false():
    m1 = cst.parse_module("import pytest\n")
    assert conv_imports.has_pytest_import(m1)
    m2 = cst.parse_module("from pytest import approx\n")
    assert conv_imports.has_pytest_import(m2)
    m3 = cst.parse_module("")
    assert not conv_imports.has_pytest_import(m3)


def test_add_pytest_import_empty_module():
    m = cst.parse_module("")
    m2 = conv_imports.add_pytest_import(m)
    assert m2.code.strip() == "import pytest"


def test_add_pytest_import_after_docstring_and_after_imports():
    src = '"""module doc"""\n\nimport os\nfrom sys import argv\n\nX = 1\n'
    m = cst.parse_module(src)
    m2 = conv_imports.add_pytest_import(m)
    code = m2.code
    assert '"""module doc"""' in code
    assert "import pytest" in code
    assert "import os" in code and "from sys import argv" in code


def test_add_pytest_import_idempotent():
    m = cst.parse_module("import pytest\n\nprint('ok')\n")
    m2 = conv_imports.add_pytest_import(m)
    assert m.code == m2.code


def test_remove_unittest_import_and_importfrom():
    imp_node = cst.Import(names=[cst.ImportAlias(name=cst.Name("unittest"))])
    res = conv_imports.remove_unittest_import(imp_node)
    assert res is cst.RemovalSentinel.REMOVE
    from_node = cst.ImportFrom(module=cst.Name("unittest"), names=[cst.ImportAlias(name=cst.Name("TestCase"))])
    res2 = conv_imports.remove_unittest_importfrom(from_node)
    assert res2 is cst.RemovalSentinel.REMOVE
    ok_node = cst.Import(names=[cst.ImportAlias(name=cst.Name("os"))])
    res3 = conv_imports.remove_unittest_import(ok_node)
    assert res3 is ok_node


def test_add_pytest_import_with_alias_and_from_variants():
    m_alias = cst.parse_module("import pytest as pt\n")
    assert conv_imports.has_pytest_import(m_alias)
    m_from = cst.parse_module("from pytest import approx\n")
    assert conv_imports.has_pytest_import(m_from)


def test_add_pytest_import_after_docstring_only_module():
    src = '"""only docstring"""\n\n# comment\nvar = 1\n'
    m = cst.parse_module(src)
    m2 = conv_imports.add_pytest_import(m)
    code = m2.code
    assert '"""only docstring"""' in code
    assert "import pytest" in code


def test_add_pytest_import_after_docstring_and_imports():
    src = '"""mod doc"""\n\nimport os\n\n'
    module = cst.parse_module(src)
    new_mod = imports.add_pytest_import(module)
    code = new_mod.code
    assert "import pytest" in code


def test_add_pytest_import_idempotent_when_present():
    src = "import pytest\n\nimport os\n"
    module = cst.parse_module(src)
    new_mod = imports.add_pytest_import(module)
    assert new_mod.code.count("import pytest") == 1


def test_has_and_add_pytest_import_when_missing():
    src = "\n# module with no pytest import\nimport os\n\n"
    module = cst.parse_module(src)
    assert not imports.has_pytest_import(module)
    new_mod = imports.add_pytest_import(module)
    assert imports.has_pytest_import(new_mod)
    new_mod2 = imports.add_pytest_import(new_mod)
    assert imports.has_pytest_import(new_mod2)


def test_remove_unittest_importfrom_and_import():
    src = "from unittest import TestCase, mock\nimport unittest\nimport something_else\n"
    module = cst.parse_module(src)
    new_body = []
    for stmt in module.body:
        if isinstance(stmt, cst.SimpleStatementLine) and stmt.body:
            first = stmt.body[0]
            if isinstance(first, cst.ImportFrom):
                res = imports.remove_unittest_importfrom(first)
                if res is cst.RemovalSentinel.REMOVE:
                    continue
                new_body.append(stmt)
            elif isinstance(first, cst.Import):
                res = imports.remove_unittest_import(first)
                if res is cst.RemovalSentinel.REMOVE:
                    continue
                new_body.append(stmt)
            else:
                new_body.append(stmt)
    new_module = cst.Module(body=new_body)
    text = new_module.code
    assert "unittest" not in text
