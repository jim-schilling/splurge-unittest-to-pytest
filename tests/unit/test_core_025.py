import os
from pathlib import Path


from splurge_unittest_to_pytest.stages import diagnostics

DOMAINS = ["core"]


def test_diagnostics_root_override(tmp_path: Path) -> None:
    # Enable diagnostics and set a custom root
    os.environ["SPLURGE_ENABLE_DIAGNOSTICS"] = "1"
    try:
        os.environ["SPLURGE_DIAGNOSTICS_ROOT"] = str(tmp_path)
        out = diagnostics.create_diagnostics_dir()
        assert out is not None
        # The created directory should be a child of the tmp_path override
        assert tmp_path in out.parents or out == tmp_path
    finally:
        os.environ.pop("SPLURGE_ENABLE_DIAGNOSTICS", None)
        os.environ.pop("SPLURGE_DIAGNOSTICS_ROOT", None)
