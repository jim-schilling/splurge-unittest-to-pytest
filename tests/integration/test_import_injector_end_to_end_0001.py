import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps import run_steps
from splurge_unittest_to_pytest.stages.steps_import_injector import DetectNeedsStep, InsertImportsStep


def test_detect_then_insert_adds_expected_imports():
    src = textwrap.dedent('''
    """Docstring"""

    def f() -> List[int]:
        p = Path('x')
        return p
    ''')

    context = {"module": cst.parse_module(src), "__stage_id__": "stages.imports"}
    steps = [DetectNeedsStep(), InsertImportsStep()]
    result = run_steps("stages.imports", "tasks.import_injector.pipeline", "import_pipeline", steps, context, {})
    new_mod = result.delta.values.get("module")
    assert new_mod is not None
    code = new_mod.code
    assert "from typing" in code or "List" in code
    assert "pathlib" in code or "from pathlib import Path" in code
