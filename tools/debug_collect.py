import libcst as cst
from libcst import MetadataWrapper
from splurge_unittest_to_pytest.stages.collector import Collector


def _run_debug() -> None:
    UNIT = """
class TestThree(unittest.TestCase):
    def setUp(self):
        x, y, z = make_vals()
        self.x = 's'
        self.y = 1
        self.z = 3.14

    def tearDown(self):
        pass
"""

    module = cst.parse_module(UNIT)
    wrapper = MetadataWrapper(module)
    collector = Collector()
    wrapper.visit(collector)
    out = collector.as_output()
    for cls_name, cls in out.classes.items():
        print("CLASS", cls_name)
        print("local_assignments:")
        for k, v in cls.local_assignments.items():
            print("  ", k, type(v), "->", v)
        print("setup_assignments:")
        for k, v in cls.setup_assignments.items():
            print("  ", k, [type(i) for i in (v if isinstance(v, list) else [v])])
        print("teardown_statements:")
        for s in cls.teardown_statements:
            print("   ", type(s), repr(cst.Module(body=[s]).code))

    print("done")


def main(*, argv: list[str] | None = None) -> int:
    # wrapper to match Option 2 keyword-only convention; argv is unused here
    _run_debug()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(argv=None))
