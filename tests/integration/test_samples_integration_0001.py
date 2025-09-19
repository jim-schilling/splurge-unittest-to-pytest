import pathlib
import libcst as cst

from splurge_unittest_to_pytest.stages.fixture_injector import fixture_injector_stage


SAMPLES_DIR = pathlib.Path(__file__).resolve().parent.parent / "unittest_pytest_samples"


def _load_sample(name: str) -> cst.Module:
    p = SAMPLES_DIR / name
    txt = p.read_text(encoding="utf8")
    return cst.parse_module(txt)


def test_process_unittest_sample_setUp_tearDown():
    mod = _load_sample("unittest_01_b.py.txt")
    ctx = {"module": mod}
    out = fixture_injector_stage(ctx)
    # ensure output module exists
    assert isinstance(out.get("module"), cst.Module)
    # after processing, ensure we didn't lose the import lines
    new_mod = out.get("module")
    assert any(
        isinstance(n, cst.SimpleStatementLine) and n.body and isinstance(n.body[0], cst.Import) for n in new_mod.body
    )


def test_process_unittest_function_testcase():
    mod = _load_sample("unittest_01_a.py.txt")
    ctx = {"module": mod}
    out = fixture_injector_stage(ctx)
    assert isinstance(out.get("module"), cst.Module)
    # ensure that if any fixture-like conversion occurred, module remains valid
    new_mod = out.get("module")
    assert new_mod.code is not None
