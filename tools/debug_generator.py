import libcst as cst
from libcst import MetadataWrapper
from splurge_unittest_to_pytest.stages.collector import Collector
from splurge_unittest_to_pytest.stages.generator import generator_stage

UNIT = """
def init_api_data():
    pass

class TestInitAPI(unittest.TestCase):
    def setUp(self):
        var_a, var_b = get_vals()
        self.var_a = str(var_a)
        self.var_b = str(var_b)

    def tearDown(self):
        cleanup()
"""

module = cst.parse_module(UNIT)
wrapper = MetadataWrapper(module)
collector = Collector()
wrapper.visit(collector)
out = collector.as_output()
ctx = {"collector_output": out, "module": module, "autocreate": True}
res = generator_stage(ctx)
nodes = res.get("fixture_nodes", [])
print("Nodes types/names:")
for n in nodes:
    t = type(n).__name__
    if isinstance(n, cst.FunctionDef):
        print("Function:", n.name.value)
    elif isinstance(n, cst.ClassDef):
        print("Class:", n.name.value)
    else:
        try:
            print(t, repr(cst.Module(body=[n]).code))
        except Exception as e:
            print(t, str(e))
