import textwrap

import libcst as cst

from splurge_unittest_to_pytest.stages.steps_import_injector import DetectNeedsStep


def _module_from_code(code: str) -> cst.Module:
    return cst.parse_module(textwrap.dedent(code))


def test_detect_needs_pytest_when_no_imports():
    code = """
    def test_foo():
        assert True
    """
    mod = _module_from_code(code)
    step = DetectNeedsStep()
    result = step.execute({"module": mod}, None)
    values = result.delta.values
    assert values.get("needs_pytest_import") is True


def test_detect_no_pytest_when_pytest_present():
    code = "import pytest\n\n@pytest.mark.slow\ndef test_bar():\n    pass\n"
    mod = _module_from_code(code)
    step = DetectNeedsStep()
    result = step.execute({"module": mod}, None)
    values = result.delta.values
    assert values.get("needs_pytest_import") is True  # explicit detection from decorators/text


def test_detect_sys_and_os_usage():
    code = "import os\n\nprint(os.getenv('X'))\nimport sys\nprint(sys.version)\n"
    mod = _module_from_code(code)
    step = DetectNeedsStep()
    result = step.execute({"module": mod}, None)
    values = result.delta.values
    assert values.get("needs_os_import") is True
    assert values.get("needs_sys_import") is True
