import pathlib
import libcst as cst
from libcst import MetadataWrapper
from splurge_unittest_to_pytest.stages.collector import Collector
from splurge_unittest_to_pytest.stages.generator import generator_stage
from splurge_unittest_to_pytest.stages.import_injector import import_injector_stage


DATA_DIR = pathlib.Path(__file__).parent.parent / "data"


def _load_bak(name: str) -> str:
    p = DATA_DIR / name
    return p.read_text()


def _run_pipeline(src: str) -> cst.Module:
    module = cst.parse_module(src)
    wrapper = MetadataWrapper(module)
    collector = Collector()
    wrapper.visit(collector)
    out = collector.as_output()
    # generator_stage returns fixture_nodes and optionally needs_typing_names
    ctx = {"collector_output": out, "module": module, "autocreate": True}
    gen_res = generator_stage(ctx)
    fixture_nodes = gen_res.get("fixture_nodes", [])
    # attach generated nodes to the original module body (simulating downstream stages)
    new_body = list(module.body) + list(fixture_nodes)
    new_module = module.with_changes(body=new_body)
    # call import_injector with typing names passed through
    inject_ctx = {"module": new_module}
    if "needs_typing_names" in gen_res:
        inject_ctx["needs_typing_names"] = gen_res["needs_typing_names"]
    res = import_injector_stage(inject_ctx)
    return res.get("module", new_module)


def test_init_api_bak_generates_typing_and_namedtuple():
    src = _load_bak("test_init_api.py.bak.txt")
    mod = _run_pipeline(src)
    text = getattr(mod, "code", "")
    # ensure typing import present
    assert "from typing import" in text
    # ensure pytest import present
    assert "import pytest" in text
    # expect a NamedTuple or fixture name derived from InitAPI
    assert "class _InitAPIData" in text or "init_api_data" in text


def test_cli_bak_basic_conversion():
    src = _load_bak("test_cli.py.bak.txt")
    mod = _run_pipeline(src)
    text = getattr(mod, "code", "")
    # We expect pytest import to be present; typing imports are optional
    assert "import pytest" in text
