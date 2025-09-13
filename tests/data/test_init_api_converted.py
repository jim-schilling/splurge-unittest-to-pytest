import os
from pathlib import Path


try:
    # Import lazily inside tests to avoid import-time failures when the
    # external dependency isn't installed in the test environment. Tests
    # will be skipped at runtime if the package is missing.
    from splurge_sql_generator import generate_class, generate_multiple_classes  # type: ignore
except Exception:  # pragma: no cover - external dependency optional in CI
    generate_class = None  # type: ignore
    generate_multiple_classes = None  # type: ignore

try:
    from tests.unit.test_utils import create_sql_with_schema  # type: ignore
except Exception:  # pragma: no cover - fallback helper for isolated runs
    from pathlib import Path


    def create_sql_with_schema(tmp_path: Path, filename: str, content: str):
        """Create a SQL file and a dummy schema file next to it.

        Returns (sql_path, schema_path) as Path objects.
        """

        sql_path = Path(tmp_path) / filename
        sql_path.write_text(content, encoding="utf-8")

        schema_path = sql_path.with_suffix(".schema.json")
        schema_path.write_text("{}", encoding="utf-8")

        return sql_path, schema_path


SQL_CONTENT = "# TestClass\n# test_method\nSELECT 1;"


def test_generate_class(tmp_path: Path) -> None:
    # Create SQL + schema in the temporary directory
    sql_file, schema_file = create_sql_with_schema(tmp_path, "test.sql", SQL_CONTENT)
    sql_path = str(sql_file)
    schema_path = str(schema_file)

    if generate_class is None:  # pragma: no cover - skip when dependency missing
        import pytest

        pytest.skip("splurge_sql_generator not installed")

    # generate_class returns the generated code as a string
    code = generate_class(sql_path, schema_file_path=schema_path)
    assert "class TestClass" in code

    # Also verify that writing to an output file works
    output_file = sql_path + ".py"
    generate_class(sql_path, output_file_path=output_file, schema_file_path=schema_path)
    assert os.path.exists(output_file)

    with open(output_file, "r", encoding="utf-8") as fh:
        content = fh.read()
    assert "class TestClass" in content


def test_generate_multiple_classes(tmp_path: Path) -> None:
    # Create SQL + schema in the temporary directory
    sql_file, schema_file = create_sql_with_schema(tmp_path, "test.sql", SQL_CONTENT)
    sql_path = str(sql_file)
    schema_path = str(schema_file)

    # Prepare output dir
    output_dir = tmp_path / "outdir"
    output_dir.mkdir()

    if generate_multiple_classes is None:  # pragma: no cover - skip when dependency missing
        import pytest

        pytest.skip("splurge_sql_generator not installed")

    # generate_multiple_classes may accept a list of paths and an output directory
    result = generate_multiple_classes([sql_path], output_dir=str(output_dir), schema_file_path=schema_path)
    assert "TestClass" in result

    out_file = output_dir / "test_class.py"
    assert out_file.exists()
    with open(out_file, "r", encoding="utf-8") as fh:
        content = fh.read()
    assert "class TestClass" in content
