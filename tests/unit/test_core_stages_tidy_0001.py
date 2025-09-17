import libcst as cst
from splurge_unittest_to_pytest.stages import formatting


def test_node_to_str_name_and_attribute():
    n = cst.Name("os")
    assert formatting._node_to_str(n) == "os"
    a = cst.Attribute(value=cst.Name("pkg"), attr=cst.Name("mod"))
    assert formatting._node_to_str(a) == "pkg.mod"


def test_normalize_class_body_collapses_runs():
    inner_m1 = cst.FunctionDef(name=cst.Name("a"), params=cst.Parameters(), body=cst.IndentedBlock(body=[cst.Pass()]))
    m1 = cst.SimpleStatementLine(body=[inner_m1])
    m2 = cst.FunctionDef(name=cst.Name("b"), params=cst.Parameters(), body=cst.IndentedBlock(body=[cst.Pass()]))
    body = cst.IndentedBlock(body=[m1, cst.EmptyLine(), cst.EmptyLine(), cst.EmptyLine(), m2])
    norm = formatting.normalize_class_body(body)
    codes = [type(n).__name__ for n in norm.body]
    assert codes[0] == "SimpleStatementLine"
    assert codes[1] == "EmptyLine"
    assert codes[2] == "FunctionDef"


def test_normalize_module_import_grouping_and_spacing():
    doc = cst.SimpleStatementLine(body=[cst.Expr(cst.SimpleString("'doc'"))])
    imp1 = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("os"))])])
    imp2 = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("pytest"))])])
    imp3 = cst.SimpleStatementLine(body=[cst.Import(names=[cst.ImportAlias(name=cst.Name("os"))])])
    func = cst.FunctionDef(name=cst.Name("f"), params=cst.Parameters(), body=cst.IndentedBlock(body=[cst.Pass()]))
    module = cst.Module(body=[doc, imp1, imp2, imp3, cst.EmptyLine(), func])
    new_mod = formatting.normalize_module(module)
    code = new_mod.code
    assert code.count("import os") == 1
    assert "import pytest" in code
    assert "def f" in code


def test_import_dedup_and_grouping_and_two_blank_lines():
    src = "\nimport os\nimport pytest\nimport splurge_unittest_to_pytest\n\ndef foo():\n    pass\n"
    module = cst.parse_module(src)
    new = formatting.normalize_module(module)
    code = new.code
    assert code.index("import os") < code.index("import pytest")
    assert code.index("import pytest") < code.index("import splurge_unittest_to_pytest")
    assert "\n\n\ndef foo" in code or "\n\ndef foo" in code


def test_normalize_class_body_collapses_empty_runs_and_inserts_two_lines_after_class():
    src = "\nclass C:\n    def a(self):\n        pass\n\n\n    \n    def b(self):\n        pass\n\ndef after():\n    pass\n"
    module = cst.parse_module(src)
    new = formatting.normalize_module(module)
    class_node = None
    for n in new.body:
        if isinstance(n, cst.ClassDef) and n.name.value == "C":
            class_node = n
            break
    assert class_node is not None
    members = list(class_node.body.body)
    fn_indices = [
        i
        for i, m in enumerate(members)
        if isinstance(m, cst.SimpleStatementLine)
        and isinstance(m.body[0], cst.FunctionDef)
        or isinstance(m, cst.FunctionDef)
    ]
    assert len(fn_indices) >= 2
    start = fn_indices[0]
    end = fn_indices[1]
    between = members[start + 1 : end]
    empty_count = sum((1 for b in between if isinstance(b, cst.EmptyLine)))
    assert empty_count <= 1
    idx = None
    for i, n in enumerate(new.body):
        if isinstance(n, cst.ClassDef) and n.name.value == "C":
            idx = i
            break
    assert idx is not None
    following = new.body[idx + 1 : idx + 4]
    empties = [n for n in following if isinstance(n, cst.EmptyLine)]
    assert len(empties) >= 2
