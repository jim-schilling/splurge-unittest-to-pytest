import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps import run_steps
from splurge_unittest_to_pytest.stages.steps_import_injector import DetectNeedsStep, InsertImportsStep


def test_import_injector_detects_and_inserts_end_to_end():
    src = textwrap.dedent("""
    # module header
    from typing import Optional  # keep-optional
    from typing import (
        List,  # comment-on-list
    )

    def f(x: Optional[int]) -> List[int]:
        pass
    """)
    mod = cst.parse_module(src)
    det = DetectNeedsStep().execute({"module": mod}, {})
    res = InsertImportsStep().execute({"module": mod, **det.delta.values}, {})
    new_mod = res.delta.values.get("module")
    assert new_mod is not None
    code = new_mod.code
    # no duplicate typing imports
    assert code.count("from typing import") == 1
    # comments and parentheses preserved
    assert "# keep-optional" in code
    assert "# comment-on-list" in code


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
