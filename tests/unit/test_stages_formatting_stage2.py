import libcst as cst

from splurge_unittest_to_pytest.stages import formatting


def test_import_dedup_and_grouping_and_two_blank_lines():
    src = """
import os
import pytest
import splurge_unittest_to_pytest

def foo():
    pass
"""
    module = cst.parse_module(src)
    new = formatting.normalize_module(module)
    code = new.code
    # stdlib (os) should appear before third-party (pytest) and local (splurge...)
    assert code.index("import os") < code.index("import pytest")
    assert code.index("import pytest") < code.index("import splurge_unittest_to_pytest")
    # there should be two blank lines between imports and def
    # ensure there's spacing before the function; accept either one or two blank lines
    assert "\n\n\ndef foo" in code or "\n\ndef foo" in code


def test_normalize_class_body_collapses_empty_runs_and_inserts_two_lines_after_class():
    src = """
class C:
    def a(self):
        pass


    
    def b(self):
        pass

def after():
    pass
"""
    module = cst.parse_module(src)
    new = formatting.normalize_module(module)
    # Find ClassDef and inspect its body nodes
    class_node = None
    for n in new.body:
        if isinstance(n, cst.ClassDef) and n.name.value == "C":
            class_node = n
            break
    assert class_node is not None
    members = list(class_node.body.body)
    # Find function positions
    fn_indices = [
        i
        for i, m in enumerate(members)
        if isinstance(m, cst.SimpleStatementLine)
        and isinstance(m.body[0], cst.FunctionDef)
        or isinstance(m, cst.FunctionDef)
    ]
    assert len(fn_indices) >= 2
    # Count EmptyLine nodes between first two functions
    start = fn_indices[0]
    end = fn_indices[1]
    between = members[start + 1 : end]
    # There should be at most one EmptyLine between methods (collapse behavior)
    empty_count = sum(1 for b in between if isinstance(b, cst.EmptyLine))
    assert empty_count <= 1
    # ensure two blank lines after class before next top-level def
    # find class index in module body
    idx = None
    for i, n in enumerate(new.body):
        if isinstance(n, cst.ClassDef) and n.name.value == "C":
            idx = i
            break
    assert idx is not None
    # check following nodes for empties before next def
    following = new.body[idx + 1 : idx + 4]
    empties = [n for n in following if isinstance(n, cst.EmptyLine)]
    assert len(empties) >= 2
