import libcst as cst
from splurge_unittest_to_pytest.stages.raises_stage import RaisesRewriter


def test_rewrites_cm_exception_to_value_when_as_used():
    src = """
class T:
    def test_it(self):
        with self.assertRaises(ValueError) as cm:
            raise ValueError('msg')
        # access
        e = cm.exception
"""
    mod = cst.parse_module(src)
    new = mod.visit(RaisesRewriter())
    code = new.code
    assert "with pytest.raises(ValueError) as cm:" in code
    # ensure attribute access changed
    assert "cm.value" in code
