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
    ctx = {"collector_output": out, "module": module, "autocreate": True}
    gen_res = generator_stage(ctx)
    fixture_nodes = gen_res.get("fixture_nodes", [])
    new_body = list(module.body) + list(fixture_nodes)
    new_module = module.with_changes(body=new_body)
    inject_ctx = {"module": new_module}
    if "needs_typing_names" in gen_res:
        inject_ctx["needs_typing_names"] = gen_res["needs_typing_names"]
    res = import_injector_stage(inject_ctx)
    return res.get("module", new_module)


def test_init_api_bak_generates_typing_and_namedtuple():
    src = _load_bak("test_init_api.py.bak.txt")
    mod = _run_pipeline(src)
    text = getattr(mod, "code", "")
    assert "from typing import" in text
    assert "import pytest" in text
    assert "class _InitAPIData" in text or "init_api_data" in text


def test_cli_bak_basic_conversion():
    src = _load_bak("test_cli.py.bak.txt")
    mod = _run_pipeline(src)
    text = getattr(mod, "code", "")
    assert "import pytest" in text


test_unit = '\nimport unittest\n\nclass TestExact(unittest.TestCase):\n    def setUp(self):\n        self.pair = ("a", 1)\n\n    def test_something(self):\n        assert self.pair[1] == 1\n'


def normalize(s: str) -> str:
    import re

    s2 = re.sub("\\s+", " ", s).strip()
    return s2


def test_golden_tuple_fixture_matches_expected(tmp_path, request):
    module = cst.parse_module(test_unit)
    wrapper = MetadataWrapper(module)
    collector = Collector()
    wrapper.visit(collector)
    out = collector.as_output()
    ctx = {"collector_output": out, "module": module}
    gen_res = generator_stage(ctx)
    nodes = gen_res.get("fixture_nodes", [])
    generated_module = cst.Module(body=list(nodes))
    inj_ctx = {"module": generated_module, "needs_typing_names": gen_res.get("needs_typing_names", [])}
    inj_res = import_injector_stage(inj_ctx)
    final_mod = inj_res.get("module")
    assert final_mod is not None
    generated_text = final_mod.code
    golden_path = request.config.rootpath / "tests" / "data" / "golden_tuple.expected"
    expected_text = golden_path.read_text(encoding="utf8")
    assert normalize(generated_text) == normalize(expected_text)
