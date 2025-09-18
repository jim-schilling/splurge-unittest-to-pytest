import libcst as cst
import pytest

from splurge_unittest_to_pytest.stages.import_injector import import_injector_stage
from tests.support.golden_compare import assert_code_equal


# TODO(pref): This test currently runs only the import injector but compares
# the result to a fully converted golden. After the stage redesign, full
# conversion happens across multiple stages. Preferred follow-up:
# 1) Rewrite this test to run the full pipeline (or convert_string) and
#    compare to the golden.
# 2) Add a separate injector-only test asserting just import insertion
#    behavior (presence/order/dedup of imports).
@pytest.mark.xfail(
    strict=False, reason="Injector alone no longer yields full conversion; use full pipeline for golden compare"
)
def test_import_injector_matches_golden(request):
    data_dir = request.config.rootpath / "tests" / "data"
    src = (data_dir / "samples" / "sample-06-unittest.txt").read_text(encoding="utf8")
    mod = cst.parse_module(src)
    ctx = {"module": mod}
    out = import_injector_stage(ctx)
    new_mod = out.get("module")
    assert new_mod is not None
    code = new_mod.code
    expected = (data_dir / "goldens" / "sample_06_converted.expected").read_text(encoding="utf8")
    ok, msg = assert_code_equal(code, expected)
    assert ok, msg
