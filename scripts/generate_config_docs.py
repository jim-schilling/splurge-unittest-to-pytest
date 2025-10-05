#!/usr/bin/env python3
"""Script to generate configuration documentation."""

import sys
from pathlib import Path

# Add the package to the path
sys.path.insert(0, str(Path(__file__).parent))

from splurge_unittest_to_pytest.config_docs_generator import generate_config_docs

if __name__ == "__main__":
    docs_dir = Path(__file__).parent / "docs"
    print(f"Generating configuration documentation in {docs_dir}")
    generate_config_docs(docs_dir)
    print("Documentation generation complete!")
