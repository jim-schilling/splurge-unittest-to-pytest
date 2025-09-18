"""Legacy wrapper that calls the package `print_diagnostics` module.

This wrapper preserves the historical `tools/print_diagnostics.py` entry
point and delegates to `splurge_unittest_to_pytest.print_diagnostics.main`.
It can be executed as a script or as a module:

    python tools/print_diagnostics.py
    python -m splurge_unittest_to_pytest.print_diagnostics

The script will use `--root`, `SPLURGE_DIAGNOSTICS_ROOT`, or the system
temporary directory to locate diagnostics runs.
"""

import sys

from splurge_unittest_to_pytest.print_diagnostics import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
