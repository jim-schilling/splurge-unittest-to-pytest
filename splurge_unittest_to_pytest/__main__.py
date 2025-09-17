"""Package __main__ entry for running the converter as a script.

Allows executing the package with ``python -m splurge_unittest_to_pytest``
to invoke the CLI entry point. The module intentionally keeps runtime
work minimal and primarily exists to provide a discoverable
``__main__`` entry.

Publics:
        None (the package CLI is exposed via the console script).
"""

DOMAINS = ["cli"]


# Associated domains for this module
# Moved to top of module after imports.
