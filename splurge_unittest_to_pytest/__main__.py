"""Main entry point for running splurge-unittest-to-pytest as a module.

This allows users to run the CLI with:
    python -m splurge_unittest_to_pytest [command] [options]
"""

from .cli import main

if __name__ == "__main__":
    main()
