import libcst as cst

from splurge_unittest_to_pytest.stages.generator_parts.shutil_detector import cleanup_needs_shutil


def test_cleanup_needs_shutil_true_for_shutil_call():
    stmt = cst.SimpleStatementLine(body=[cst.Expr(cst.Call(func=cst.Attribute(value=cst.Name('shutil'), attr=cst.Name('rmtree')), args=[]))])
    assert cleanup_needs_shutil([stmt])


def test_cleanup_needs_shutil_true_for_import():
    stmt = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name('shutil'))])])
    assert cleanup_needs_shutil([stmt])


def test_cleanup_needs_shutil_false_for_unrelated():
    stmt = cst.SimpleStatementLine(body=[cst.Expr(cst.Call(func=cst.Name('print'), args=[cst.Arg(cst.SimpleString('"x"'))]))])
    assert not cleanup_needs_shutil([stmt])
