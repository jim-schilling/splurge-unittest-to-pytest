Pre-commit setup

This repository uses system-installed tools for the pre-commit hooks (ruff, mypy, pytest). The steps below show how to enable and run the hooks in both bash (Git Bash or WSL) and PowerShell on Windows. They assume this project uses the included virtual environment at `.venv`.

1) Activate the virtual environment

bash (Git Bash / WSL):

```bash
source /D/repos/splurge-unittest-to-pytest/.venv/Scripts/activate
```

PowerShell:

```powershell
& D:\repos\splurge-unittest-to-pytest\.venv\Scripts\Activate.ps1
```

2) Install developer dependencies (recommended)

This installs pre-commit plus the versions of ruff, mypy, pytest, and other tools we use for local verification.

```bash
python -m pip install -r requirements-dev.txt
```

3) Install pre-commit hooks (one-time)

```bash
pre-commit install
```

4) Run hooks across the repository (recommended before committing)

```bash
pre-commit run --all-files
```

Global install (optional)

If you prefer to install pre-commit and tools globally (not in a virtual environment), run:

```bash
python -m pip install --user pre-commit ruff mypy pytest pytest-cov
```

After installing, run the same one-time install and run commands from above:

```bash
pre-commit install
pre-commit run --all-files
```

Notes and troubleshooting

- The pre-commit config is set to use system-installed tools and sets pass_filenames: false for mypy and pytest hooks. That prevents pre-commit from appending file lists to the hook commands (mypy disallows mixing -p with file args).
- On Windows you may see intermittent coverage plugin errors about parallel data files when running the full test suite via the pre-commit pytest hook; if that happens, re-run with the pytest flags we use in CI or run pytest directly, for example:

  ```bash
  pytest -q tests/unit
  ```

- If your environment uses a different venv path, replace the activation command above with the correct path to your virtualenv's activation script.
- If you prefer to use system packages (not a venv), ensure ruff, mypy, pytest and pre-commit are installed and available on PATH before running `pre-commit install`.

That's it — once installed, pre-commit will run the configured hooks automatically on commit and you can run them manually with `pre-commit run --all-files`.
