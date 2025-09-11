Pre-commit setup

Install pre-commit in your environment and enable hooks:

    python -m pip install pre-commit
    pre-commit install

Run hooks across the repository:

    pre-commit run --all-files

This repository config runs ruff, mypy, and the unit tests under `tests/unit/`.
